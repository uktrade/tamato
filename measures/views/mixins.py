from typing import Type
from typing import Dict

from common.models import TrackedModel
from measures import models
from workbaskets.forms import SelectableObjectsForm
from workbaskets.models import WorkBasket
from workbaskets.session_store import SessionStore


class MeasureMixin:
    model: Type[TrackedModel] = models.Measure

    def get_queryset(self):
        tx = WorkBasket.get_current_transaction(self.request)

        return models.Measure.objects.approved_up_to_transaction(tx)


class MeasureSessionStoreMixin:
    @property
    def session_store(self):
        return SessionStore(
            self.request,
            "MULTIPLE_MEASURE_SELECTIONS",
        )


class MeasureSelectionMixin(MeasureSessionStoreMixin):
    @property
    def measure_selections(self):
        """Get the IDs of measure that are candidates for editing/deletion."""
        return [
            SelectableObjectsForm.object_id_from_field_name(name)
            for name in [*self.session_store.data]
        ]

    @property
    def measure_selectors(self):
        """
        Used for JavaScript.

        Get the checkbox names of measure that are candidates for
        editing/deletion.
        """
        return list(self.session_store.data.keys())


class MeasureSelectionQuerysetMixin(MeasureSelectionMixin):
    def get_queryset(self):
        """Get the queryset for measures that are candidates for
        editing/deletion."""
        return models.Measure.objects.filter(pk__in=self.measure_selections)


class MeasureSerializableWizardMixin:
    """A Mixin for the wizard forms that utilise asynchronous bulk processing. This mixin provides the functionality to go through each form
    and serialize the data ready for storing in the database."""

    def get_data_form_list(self) -> dict:
        """
        Returns a form list based on form_list, conditionally including only
        those items as per condition_list and also appearing in data_form_list.
        The list is generated dynamically because conditions in condition_list
        may be dynamic.
        Essentially, version of `WizardView.get_form_list()` filtering in only
        those list items appearing in `data_form_list`.
        """
        data_form_keys = [key for key, form in self.data_form_list]
        return {
            form_key: form_class
            for form_key, form_class in self.get_form_list().items()
            if form_key in data_form_keys
        }

    def all_serializable_form_data(self) -> Dict:
        """
        Returns serializable data for all wizard steps.
        This is a re-implementation of
        MeasureCreateWizard.get_all_cleaned_data(), but using self.data after
        is_valid() has been successfully run.
        """

        all_data = {}

        for form_key in self.get_data_form_list().keys():
            all_data[form_key] = self.serializable_form_data_for_step(form_key)

        return all_data

    def serializable_form_data_for_step(self, step) -> Dict:
        """
        Returns serializable data for a wizard step.
        This is a re-implementation of WizardView.get_cleaned_data_for_step(),
        returning the serializable version of data in place of the form's
        regular cleaned_data.
        """

        form_obj = self.get_form(
            step=step,
            data=self.storage.get_step_data(step),
            files=self.storage.get_step_files(step),
        )

        return form_obj.serializable_data(remove_key_prefix=step)

    def all_serializable_form_kwargs(self) -> Dict:
        """Returns serializable kwargs for all wizard steps."""

        all_kwargs = {}

        for form_key in self.get_data_form_list().keys():
            all_kwargs[form_key] = self.serializable_form_kwargs_for_step(form_key)

        return all_kwargs

    def serializable_form_kwargs_for_step(self, step) -> Dict:
        """Returns serializable kwargs for a wizard step."""

        form_kwargs = self.get_form_kwargs(step)
        form_class = self.form_list[step]

        return form_class.serializable_init_kwargs(form_kwargs)
