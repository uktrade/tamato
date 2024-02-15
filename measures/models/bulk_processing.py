import json
import logging
from typing import Dict
from typing import Iterable

from celery.result import AsyncResult
from django.db import models
from django.db.models.deletion import SET_NULL
from django.db.transaction import atomic
from django.forms.formsets import BaseFormSet

from common.celery import app
from common.models import Transaction
from common.models.utils import set_current_transaction
from measures.models.tracked_models import Measure

logger = logging.getLogger(__name__)


class DateTimeStampedMixin:
    """Mixin to add `created_at` (using `auto_now_add=True`) and `updated_at`
    (using `auto_now=True`) `DateTimeField` attributes to `Model` classes."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


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
    """Processing now completed with a failure outcome - failed to screate
    measures."""
    CANCELLED = (
        "CANCELLED",
        "Cancelled",
    )
    """Processing has been cancelled."""

    @classmethod
    def queued_states(cls):
        """Returns all states that represent a queued  instance, including those
        that are being processed."""
        return (
            cls.AWAITING_PROCESSING,
            cls.CURRENTLY_PROCESSING,
        )

    @classmethod
    def done_processing_states(cls):
        """Returns all states that represent a task that has completed its
        processing with either a successful or failed outcome."""
        return (
            cls.SUCCESSFULLY_PROCESSED,
            cls.FAILED_PROCESSING,
        )


class BulkProcessorResult(DateTimeStampedMixin, models.Model):
    """Result details of bulk operation."""

    succeeded = models.BooleanField(
        default=False,
    )
    """True if a bulk operation succeeded, False otherwise."""

    created_transaction = models.ForeignKey(
        "common.Transaction",
        on_delete=SET_NULL,
        null=True,
        editable=False,
    )
    """The transaction associated with a successful bulk creation."""


class BulkProcessorMixin(DateTimeStampedMixin):
    """Mixin defining common attributes and functions on bulk processing Model
    classes."""

    task_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        unique=True,
    )
    """ID of the Celery task used to create measures - blank=True + null=True
    is required to allow multiple blank instances with unique=True."""

    processing_result = models.ForeignKey(
        "measures.BulkProcessorResult",
        on_delete=SET_NULL,
        null=True,
        editable=False,
    )
    """The result of a bulk processing action (e.g. measures bulk creation) -
    NULL until the creation has run to completion."""

    @property
    def processing_state(self) -> ProcessingState:
        """Calculates and returns the current processing state."""

        AsyncResult(self.task_id)
        # TODO: Dynamically calculate state or use a FSM?
        return ProcessingState.AWAITING_PROCESSING

    def schedule(self) -> AsyncResult:
        """
        Prototype of function that must be implemented by this mixin's subclass.

        Implementations of this function should schedule the processing task
        (using `delay()` or `apply_async()`), returning the resulting Celery
        AsyncResult object.
        """
        raise NotImplementedError


class MeasuresBulkCreatorManager(models.Manager):
    """Model Manager for MeasuresBulkCreator models."""

    def create(
        self,
        form_data: Dict,
        form_kwargs: Dict,
        current_transaction: Transaction,
        **kwargs,
    ) -> "MeasuresBulkCreator":
        """Create and save an instance of MeasuresBulkCreator."""
        return super().create(
            form_data=form_data,
            form_kwargs=form_kwargs,
            current_transaction=current_transaction,
            workbasket=current_transaction.workbasket,
            **kwargs,
        )


def REVOKE_TASKS_AND_SET_NULL(collector, field, sub_objs, using):
    """Revoke any celery bulk editing tasks, identified via a `task_id` field,
    on the object and set the foreign key value to NULL."""
    for obj in sub_objs:
        if hasattr(obj, "task_id"):
            app.control.revoke(obj.task_id, terminate=True)
    SET_NULL(collector, field, sub_objs, using)


class MeasuresBulkCreator(BulkProcessorMixin, models.Model):
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

    current_transaction = models.ForeignKey(
        "common.Transaction",
        on_delete=REVOKE_TASKS_AND_SET_NULL,
        null=True,
        related_name="measures_bulk_creators",
        editable=False,
    )
    """
    The 'current' Transaction instance at the time `form_data` was constructed.

    This is normally set by
    `common.models.utils.TransactionMiddleware` when processing a HTTP request
    and can be obtained from `common.models.utils.get_current_transaction()`
    to capture its value.
    """

    workbasket = models.ForeignKey(
        "workbaskets.WorkBasket",
        on_delete=REVOKE_TASKS_AND_SET_NULL,
        null=True,
        editable=False,
    )
    """The workbasket with which created measures are associated."""

    @property
    def expected_measures_count(self):
        # TODO: return number of measures being created.

        # The number of measures created depends on two parts: the commodity
        # count and the geo areas the measure is to be applied to.
        # The geo area count is per area BEFORE ommissions, ie. each country
        # group/erga omnes, with an excluded country, still counts as a single
        # entity.
        # Measures to be created = commodity count * geo_area

        # Hard coded until the create method has been refactored.
        return 5

    @atomic
    def create_measures(self) -> Iterable[Measure]:
        """Create measures using the instance's `cleaned_data`, returning the
        results as an iterable."""

        created_measures = []

        # Construction and / or validation of some Form instances require
        # access to a 'current' Transaction.
        set_current_transaction(self.current_transaction)

        logger.info(
            f"MeasuresBulkCreator.create_measures() - form_data:\n"
            f"{json.dumps(self.form_data, indent=4, default=str)}",
        )
        logger.info(
            f"MeasuresBulkCreator.create_measures() - form_kwargs:\n"
            f"{json.dumps(self.form_kwargs, indent=4, default=str)}",
        )

        # Avoid circular import.
        from measures.views import MeasureCreateWizard

        for form_key, form_class in MeasureCreateWizard.data_form_list:
            if form_key not in self.form_data:
                # Not all forms / steps are used to create measures. Some are
                # only conditionally included - see `MeasureCreateWizard.condition_dict`
                # and `MeasureCreateWizard.show_step()` for details.
                continue

            data = self.form_data[form_key]
            kwargs = form_class.deserialize_init_kwargs(self.form_kwargs[form_key])
            form = form_class(data=data, **kwargs)
            form = MeasureCreateWizard.fixup_form(form, self.current_transaction)
            is_valid = form.is_valid()

            logger.info(
                f"MeasuresBulkCreator.create_measures() - "
                f"{form_class.__name__}.is_valid(): {is_valid}",
            )
            if not is_valid:
                self._log_form_errors(form_class=form_class, form_or_formset=form)

        # TODO: Create the measures.

        return created_measures

    def schedule(self) -> AsyncResult:
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

    def _log_form_errors(self, form_class, form_or_formset) -> None:
        """Output errors associated with a Form or Formset instance, handling
        output for each instance type in a uniform manner."""

        logger.error(
            f"MeasuresBulkCreator.create_measures() - "
            f"{form_class.__name__} has {len(form_or_formset.errors)} unexpected "
            f"errors.",
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
