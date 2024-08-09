import json
import logging
from typing import Dict
from typing import Iterable
from typing import Tuple

from celery.result import AsyncResult
from django.conf import settings
from django.db import models
from django.db.models.deletion import SET_NULL
from django.db.transaction import atomic
from django.forms import ValidationError
from django.forms.formsets import BaseFormSet
from django_fsm import FSMField
from django_fsm import transition

from common.celery import app
from common.models.mixins import TimestampedMixin
from common.models.utils import override_current_transaction
from common.util import TaricDateRange
from common.validators import UpdateType
from measures.models.tracked_models import Measure
from measures.util import update_measure_components
from measures.util import update_measure_condition_components
from measures.util import update_measure_excluded_geographical_areas
from measures.util import update_measure_footnote_associations

logger = logging.getLogger(__name__)


class ProcessingState(models.TextChoices):
    """Available states of bulk creational tasks."""

    AWAITING_PROCESSING = (
        "AWAITING_PROCESSING",
        "Awaiting processing",
    )
    """Queued up and awaiting processing."""
    CURRENTLY_PROCESSING = (
        "CURRENTLY_PROCESSING",
        "Currently processing",
    )
    """Picked off the queue and now currently being processed - now attempting
    to bulk create measures."""
    SUCCESSFULLY_PROCESSED = (
        "SUCCESSFULLY_PROCESSED",
        "Successfully processed",
    )
    """Processing now completed with a successful outcome - successfully created
    measures."""
    FAILED_PROCESSING = (
        "FAILED_PROCESSING",
        "Failed processing",
    )
    """Processing now completed with a failure outcome - failed to create
    measures."""
    CANCELLED = (
        "CANCELLED",
        "Cancelled",
    )
    """Processing has been cancelled."""

    @classmethod
    def queued_states(cls) -> Tuple:
        """Returns all states that represent a queued  instance, including those
        that are being processed."""
        return (
            cls.AWAITING_PROCESSING,
            cls.CURRENTLY_PROCESSING,
        )

    @classmethod
    def done_processing_states(cls) -> Tuple:
        """Returns all states that represent a task that has completed its
        processing with either a successful or failed outcome."""
        return (
            cls.SUCCESSFULLY_PROCESSED,
            cls.FAILED_PROCESSING,
        )


class BulkProcessor(TimestampedMixin):
    """(Abstract) Model mixin defining common attributes and functions for
    inheritace by Model classes responsible for asynchronously bulk processing
    tasks."""

    class Meta:
        abstract = True

    task_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        unique=True,
    )
    """ID of the Celery task used to create measures - blank=True + null=True
    is required to allow multiple blank instances with unique=True."""

    processing_state = FSMField(
        default=ProcessingState.AWAITING_PROCESSING,
        choices=ProcessingState.choices,
        db_index=True,
        protected=True,
        editable=False,
    )
    """
    Current state of the BulkProcessor instance.

    This attribute is driven through valid transitions by the member functions
    on on this class that are annotated by @transition.
    """

    successfully_processed_count = models.PositiveIntegerField(
        default=0,
    )
    """
    The number of objects processed by a bulk creation task.

    Its value is set when the processor has successfully completed and maintains
    its default value of zero otherwise.
    """

    def schedule_task(self) -> AsyncResult:
        """
        Prototype of function that must be implemented by this mixin's subclass.

        Implementations of this function should schedule the processing task
        (using `delay()` or `apply_async()`), returning the resulting Celery
        AsyncResult object, and save the resulting task's id as
        `BulkProcessor.task_id`. For example:

        ```
        def schedule_task(self) -> AsyncResult:
            async_result = bulk_creator_fn.delay()
            self.task_id = async_result.id
            self.save()
            return async_result
        ```
        """
        raise NotImplementedError

    def cancel_task(self) -> None:
        """
        Attempt cancelling a task that has previously been queued using
        schedule_task(), transition processing_state to CANCELLED and save the
        instance (if the instance is in a valid current state).

        If the instance
        `processing_state` is not in one of the queued_states, then no state
        change is applied to the instance.
        """

        if self.task_id:
            app.control.revoke(self.task_id, terminate=True)
            logger.info(
                f"BulkProcessor.cancel_task(): BulkProcessor({self.pk})'s "
                f"task({self.task_id}) revoked.",
            )

        if self.processing_state in ProcessingState.queued_states():
            self.processing_cancelled()
            self.save()

    # ---
    # Methods used to drive `procssing_state` through valid state transitions.
    # ---

    @transition(
        field=processing_state,
        source=ProcessingState.AWAITING_PROCESSING,
        target=ProcessingState.CURRENTLY_PROCESSING,
        custom={"label": "Start processing"},
    )
    def begin_processing(self) -> None:
        """Begin procssing from an initial awaiting state."""

    @transition(
        field=processing_state,
        source=ProcessingState.CURRENTLY_PROCESSING,
        target=ProcessingState.SUCCESSFULLY_PROCESSED,
        custom={"label": "Processing succeeded"},
    )
    def processing_succeeded(self) -> None:
        """Processing completed with a successful outcome."""

    @transition(
        field=processing_state,
        source=ProcessingState.CURRENTLY_PROCESSING,
        target=ProcessingState.FAILED_PROCESSING,
        custom={"label": "Processing failed"},
    )
    def processing_failed(self) -> None:
        """Procssing completed with a failed outcome."""

    @transition(
        field=processing_state,
        source=(
            ProcessingState.AWAITING_PROCESSING,
            ProcessingState.CURRENTLY_PROCESSING,
        ),
        target=ProcessingState.CANCELLED,
        custom={"label": "Processing cancelled"},
    )
    def processing_cancelled(self) -> None:
        """Procssing was cancelled before completion."""


class MeasuresBulkCreatorManager(models.Manager):
    """Model Manager for MeasuresBulkCreator models."""

    def create(
        self,
        form_data: Dict,
        form_kwargs: Dict,
        workbasket,
        user,
        **kwargs,
    ) -> "MeasuresBulkCreator":
        """Create and save an instance of MeasuresBulkCreator."""

        return super().create(
            form_data=form_data,
            form_kwargs=form_kwargs,
            workbasket=workbasket,
            user=user,
            **kwargs,
        )


def REVOKE_TASKS_AND_SET_NULL(collector, field, sub_objs, using) -> None:
    """
    Revoke any celery bulk editing tasks, identified via a `task_id` field, on
    the object and set the foreign key value to NULL.

    Note: Although this function signature is the same as for other functions
    that may be used with the `on_delete` parameter, it should only be used by
    subclasses of BulkProcessor.
    """
    for obj in sub_objs:
        if isinstance(obj, BulkProcessor):
            obj.cancel_task()
    SET_NULL(collector, field, sub_objs, using)


class MeasuresBulkCreator(BulkProcessor):
    """
    Model class used to bulk create Measures instances from serialized form
    data.

    The stored form data is serialized and deserialized by Forms that subclass
    SerializableFormMixin.
    """

    objects = MeasuresBulkCreatorManager()

    form_data = models.JSONField()
    """Dictionary of all Form.data, used to reconstruct bound Form instances as
    if the form data had been sumbitted by the user within the measure wizard
    process."""

    form_kwargs = models.JSONField()
    """Dictionary of all form init data, excluding a form's `data` param (which
    is preserved via this class's `form_data` attribute)."""

    workbasket = models.ForeignKey(
        "workbaskets.WorkBasket",
        on_delete=REVOKE_TASKS_AND_SET_NULL,
        null=True,
        editable=False,
    )
    """The workbasket with which created measures are associated."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=SET_NULL,
        null=True,
        editable=False,
    )
    """The user who submitted the task to create measures."""

    def schedule_task(self) -> AsyncResult:
        """Implementation of base class method."""

        from measures.tasks import bulk_create_measures

        async_result = bulk_create_measures.apply_async(
            kwargs={
                "measures_bulk_creator_pk": self.pk,
            },
            countdown=1,
        )
        self.task_id = async_result.id
        self.save()

        logger.info(
            f"Measure bulk creation scheduled on task with ID {async_result.id}"
            f"using MeasuresBulkCreator.pk={self.pk}.",
        )

        return async_result

    @property
    def expected_measures_count(self) -> int:
        """
        Return the number of measures that should be created when using this
        `MeasuresBulkCreator`'s form_data.

        If validation issues are encountered in form_data, then None is returned
        (since it isn't possible to construct the necessary cleaned data that is
        required to obtain the measures count).
        """

        with override_current_transaction(
            transaction=self.workbasket.current_transaction,
        ):
            from measures.creators import MeasuresCreator

            try:
                cleaned_data = self.get_forms_cleaned_data()
            except ValidationError:
                return None

            measures_creator = MeasuresCreator(self.workbasket, cleaned_data)

            return measures_creator.expected_measures_count

    @atomic
    def create_measures(self) -> Iterable[Measure]:
        """
        Create measures using the instance's `cleaned_data`, returning the
        results as an iterable.

        ValidationError exceptions, which may be raised when constructing
        cleaned data, are not caught by this function, so should be caught or
        somehow dealt with by its callers.
        """

        logger.info(
            f"MeasuresBulkCreator.create_measures() - form_data:\n"
            f"{json.dumps(self.form_data, indent=4, default=str)}",
        )
        logger.info(
            f"MeasuresBulkCreator.create_measures() - form_kwargs:\n"
            f"{json.dumps(self.form_kwargs, indent=4, default=str)}",
        )

        with override_current_transaction(
            transaction=self.workbasket.current_transaction,
        ):
            from measures.creators import MeasuresCreator

            cleaned_data = self.get_forms_cleaned_data()
            measures_creator = MeasuresCreator(self.workbasket, cleaned_data)

            return measures_creator.create_measures()

    def get_forms_cleaned_data(self) -> Dict:
        """
        Returns a merged dictionary of all Form cleaned_data.

        If a Form's data contains a `FormSet`, the key will be prefixed with
        "formset-" and contain a list of the formset cleaned_data dictionaries.

        If form validation errors are encountered when constructing cleaned
        data, then this function raises Django's `ValidationError` exception.
        """

        all_cleaned_data = {}

        from measures.views import MeasureCreateWizard

        for form_key, form_class in MeasureCreateWizard.data_form_list:
            if form_key not in self.form_data:
                # Forms are conditionally included during step processing - see
                # `MeasureCreateWizard.show_step()` for details.
                continue

            data = self.form_data[form_key]
            kwargs = form_class.deserialize_init_kwargs(self.form_kwargs[form_key])
            form = form_class(data=data, **kwargs)
            form = MeasureCreateWizard.fixup_form(
                form,
                self.workbasket.current_transaction,
            )

            if not form.is_valid():
                self._log_form_errors(form_class=form_class, form_or_formset=form)
                raise ValidationError(
                    f"{form_class.__name__} has {len(form.errors)} errors.",
                )

            if isinstance(form.cleaned_data, (tuple, list)):
                all_cleaned_data[f"formset-{form_key}"] = form.cleaned_data
            else:
                all_cleaned_data.update(form.cleaned_data)

        return all_cleaned_data

    def _log_form_errors(self, form_class, form_or_formset) -> None:
        """Output errors associated with a Form or Formset instance, handling
        output for each instance type in a uniform manner."""

        logger.error(
            f"MeasuresBulkCreator.create_measures() - "
            f"{form_class.__name__} has {len(form_or_formset.errors)} errors.",
        )

        # Form.errors is a dictionary of errors, but FormSet.errors is a
        # list of dictionaries of Form.errors. Access their errors in
        # a uniform manner.
        errors = []

        if isinstance(form_or_formset, BaseFormSet):
            errors = [
                {"formset_errors": form_or_formset.non_form_errors()},
            ] + form_or_formset.errors
        else:
            errors = [form_or_formset.errors]

        for form_errors in errors:
            for error_key, error_values in form_errors.items():
                logger.error(f"{error_key}: {error_values}")



class MeasuresBulkEditorManager(models.Manager):
    """Model Manager for MeasuresBulkEditor models."""

    def create(
        self,
        form_data: Dict,
        form_kwargs: Dict,
        workbasket,
        user,
        selected_measures,
        **kwargs,
    ) -> "MeasuresBulkCreator":
        """Create and save an instance of MeasuresBulkEditor."""

        return super().create(
            form_data=form_data,
            form_kwargs=form_kwargs,
            workbasket=workbasket,
            user=user,
            selected_measures=selected_measures,
            **kwargs,
        )


class MeasuresBulkEditor(BulkProcessor):
    """
    Model class used to bulk edit Measures instances from serialized form
    data.
    The stored form data is serialized and deserialized by Forms that subclass
    SerializableFormMixin.
    """

    objects = MeasuresBulkEditorManager()

    form_data = models.JSONField()
    """Dictionary of all Form.data, used to reconstruct bound Form instances as
    if the form data had been sumbitted by the user within the measure wizard
    process."""

    form_kwargs = models.JSONField()
    """Dictionary of all form init data, excluding a form's `data` param (which
    is preserved via this class's `form_data` attribute)."""

    selected_measures = models.JSONField()
    """List of all measures that have been selected for bulk editing."""

    workbasket = models.ForeignKey(
        "workbaskets.WorkBasket",
        on_delete=REVOKE_TASKS_AND_SET_NULL,
        null=True,
        editable=False,
    )
    """The workbasket with which created measures are associated."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=SET_NULL,
        null=True,
        editable=False,
    )
    """The user who submitted the task to create measures."""

    def schedule_task(self) -> AsyncResult:
        """Implementation of base class method."""

        from measures.tasks import bulk_edit_measures

        async_result = bulk_edit_measures.apply_async(
            kwargs={
                "measures_bulk_editor_pk": self.pk,
            },
            countdown=1,
        )
        self.task_id = async_result.id
        self.save()

        logger.info(
            f"Measure bulk edit scheduled on task with ID {async_result.id}"
            f"using MeasuresBulkEditor.pk={self.pk}.",
        )

        return async_result
    
    @atomic
    def edit_measures(self) -> Iterable[Measure]:
        logger.info("INSIDE EDIT MEASURES TASK")
        # Clean the forms to get the data back out of them
        cleaned_data = self.get_forms_cleaned_data()

        logger.info(f"TASK - CLEANED DATA: {cleaned_data}")
        logger.info(f"TASK - SELF.SELECTED MEASURES: {self.selected_measures}")

        deserialized_selected_measures = Measure.objects.filter(pk__in=self.selected_measures)

        new_exclusions = [
            e["excluded_area"]
            for e in cleaned_data.get("formset-geographical_area_exclusions", [])
        ]

        if deserialized_selected_measures:
            logger.info("MADE IT TO IF SELECTED MEASURES!!!")
            for measure in deserialized_selected_measures:
                new_measure = measure.new_version(
                    workbasket=self.workbasket,
                    update_type=UpdateType.UPDATE,
                    valid_between=TaricDateRange(
                        lower=(
                            cleaned_data['start_date']
                            if cleaned_data['start_date']
                            else measure.valid_between.lower
                        ),
                        upper=(
                            cleaned_data['end_date']
                            if cleaned_data['end_date'] is not False
                            else measure.valid_between.upper
                        ),
                    ),
                    order_number=(
                        cleaned_data['order_number']
                        if cleaned_data['order_number']
                        else measure.order_number
                    ),
                    generating_regulation=(
                        cleaned_data['generating_regulation']
                        if cleaned_data['generating_regulation']
                        else measure.generating_regulation
                    ),
                )
                update_measure_components(
                    measure=new_measure,
                    duties=cleaned_data['duties'],
                    workbasket=self.workbasket,
                )
                update_measure_condition_components(
                    measure=new_measure,
                    workbasket=self.workbasket,
                )
                update_measure_excluded_geographical_areas(
                    edited="geographical_area_exclusions"
                    in cleaned_data.get("fields_to_edit", []),
                    measure=new_measure,
                    exclusions=new_exclusions,
                    workbasket=self.workbasket,
                )
                update_measure_footnote_associations(
                    measure=new_measure,
                    workbasket=self.workbasket,
                )

    def get_forms_cleaned_data(self) -> Dict:
        """
        Returns a merged dictionary of all Form cleaned_data.

        If a Form's data contains a `FormSet`, the key will be prefixed with
        "formset-" and contain a list of the formset cleaned_data dictionaries.

        If form validation errors are encountered when constructing cleaned
        data, then this function raises Django's `ValidationError` exception.
        """
        all_cleaned_data = {}

        from measures.views import MeasureEditWizard
        for form_key, form_class in MeasureEditWizard.data_form_list:

            if form_key not in self.form_data:
                # Forms are conditionally included during step processing - see
                # `MeasureEditWizard.show_step()` for details.
                continue

            data = self.form_data[form_key]

            kwargs = form_class.deserialize_init_kwargs(self.form_kwargs[form_key])

            form = form_class(data=data, **kwargs)

            if not form.is_valid():
                self._log_form_errors(form_class=form_class, form_or_formset=form)
                raise ValidationError(
                    f"{form_class.__name__} has {len(form.errors)} errors.",
                )

            if isinstance(form.cleaned_data, (tuple, list)):
                all_cleaned_data[f"formset-{form_key}"] = form.cleaned_data
            else:
                all_cleaned_data.update(form.cleaned_data)

        return all_cleaned_data

    def _log_form_errors(self, form_class, form_or_formset) -> None:
        """Output errors associated with a Form or Formset instance, handling
        output for each instance type in a uniform manner."""

        logger.error(
            f"MeasuresBulkEditor.edit_measures() - "
            f"{form_class.__name__} has {len(form_or_formset.errors)} errors.",
        )

        # Form.errors is a dictionary of errors, but FormSet.errors is a
        # list of dictionaries of Form.errors. Access their errors in
        # a uniform manner.
        errors = []

        if isinstance(form_or_formset, BaseFormSet):
            errors = [
                {"formset_errors": form_or_formset.non_form_errors()},
            ] + form_or_formset.errors
        else:
            errors = [form_or_formset.errors]

        for form_errors in errors:
            for error_key, error_values in form_errors.items():
                logger.error(f"{error_key}: {error_values}")