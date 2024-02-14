import json
import logging
from typing import Iterable

from django.db import models
from django.db.transaction import atomic
from django.forms.formsets import BaseFormSet

from common.models.utils import set_current_transaction
from measures.models.tracked_models import Measure

logger = logging.getLogger(__name__)


class MeasuresBulkCreator(models.Model):
    """
    Model class used to bulk create Measures instances from serialized form
    data.

    The stored form data is serialized and deserialized by Forms that subclass
    SerializableFormMixin.
    """

    form_data = models.JSONField()
    """Dictionary of all Form.data, used to reconstruct bound Form instances as
    if the form data had been sumbitted by the user within the measure wizard
    process."""

    form_kwargs = models.JSONField()
    """Dictionary of all form init data, excluding a form's `data` param (which
    is preserved via this class's `form_data` attribute)."""

    current_transaction = models.ForeignKey(
        "common.Transaction",
        on_delete=models.SET_NULL,
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

    # TODO:
    # - Is it preferable to save the Workbasket rather than the current
    #   transaction in the workbasket?
    #   The current transaction can change if more transactions are created
    #   before create_meassures() has chance to run. That could be good (we
    #   want objects at the time the user performed the create measures action)
    #   or bad (the current transaction may get deleted).
    #   However if workbasket immutability is guarenteed until create_measures()
    #   has completed, then this is moot. It'd need a 'protected' attribute, or
    #   something like that, on the WorkBasket class that freezes it, say, in
    #   the save() and update() methods.

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
