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


class MeasureSerializableWizardMixin():
    # Make this work
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

    def get_all_cleaned_data(self):
        """
        Returns a merged dictionary of all step cleaned_data. If a step contains
        a `FormSet`, the key will be prefixed with 'formset-' and contain a list
        of the formset cleaned_data dictionaries, as expected in
        `create_measures()`.

        Note: This patched version of `super().get_all_cleaned_data()` takes advantage of retrieving previously-saved
        cleaned_data by summary page to avoid revalidating forms unnecessarily.
        """
        all_cleaned_data = {}
        for form_key in self.get_form_list():
            cleaned_data = self.get_cleaned_data_for_step(form_key)
            if isinstance(cleaned_data, (tuple, list)):
                all_cleaned_data.update(
                    {
                        f"formset-{form_key}": cleaned_data,
                    },
                )
            else:
                all_cleaned_data.update(cleaned_data)
        return all_cleaned_data

    def get_cleaned_data_for_step(self, step):
        """
        Returns cleaned data for a given `step`.

        Note: This patched version of `super().get_cleaned_data_for_step` temporarily saves the cleaned_data
        to provide quick retrieval should another call for it be made in the same request (as happens in
        `get_form_kwargs()` and template for summary page) to avoid revalidating forms unnecessarily.
        """
        self.cleaned_data = getattr(self, "cleaned_data", {})
        if step in self.cleaned_data:
            return self.cleaned_data[step]

        self.cleaned_data[step] = super().get_cleaned_data_for_step(step)
        return self.cleaned_data[step]