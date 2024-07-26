import json
from typing import Any

from crispy_forms_gds.helper import FormHelper
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.http import JsonResponse
from django.urls import reverse
from django.views.generic import View

from common.forms import unprefix_formset_data
from common.validators import UpdateType
from common.views import TrackedModelDetailMixin
from common.views import TrackedModelDetailView
from measures import forms
from measures import models
from measures.constants import MEASURE_CONDITIONS_FORMSET_PREFIX
from measures.parsers import DutySentenceParser
from measures.patterns import MeasureCreationPattern
from workbaskets.models import WorkBasket
from workbaskets.views.generic import CreateTaricUpdateView

from . import MeasureMixin
from . import MeasureSessionStoreMixin


class MeasureUpdateBase(
    MeasureMixin,
    TrackedModelDetailMixin,
    CreateTaricUpdateView,
):
    form_class = forms.MeasureForm
    permission_required = "common.change_trackedmodel"
    queryset = models.Measure.objects.all()

    def get_template_names(self):
        return "measures/edit.jinja"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def get_form(self, form_class=None):
        form = super().get_form(form_class=form_class)
        tx = WorkBasket.get_current_transaction(self.request)

        if hasattr(form, "field"):
            for field in form.fields.values():
                if hasattr(field, "queryset"):
                    field.queryset = field.queryset.approved_up_to_transaction(tx)

        return form

    def get_footnotes(self, measure):
        tx = WorkBasket.get_current_transaction(self.request)
        associations = (
            models.FootnoteAssociationMeasure.objects.approved_up_to_transaction(
                tx,
            ).filter(
                footnoted_measure__sid=measure.sid,
            )
        )

        return [a.associated_footnote for a in associations]

    def get_conditions(self, measure):
        tx = WorkBasket.get_current_transaction(self.request)
        return (
            measure.conditions.with_reference_price_string().approved_up_to_transaction(
                tx,
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["no_form_tags"] = FormHelper()
        context["no_form_tags"].form_tag = False

        formset_footnotes = self.request.session.get(
            f"formset_initial_{self.kwargs.get('sid')}",
            [],
        )
        footnotes_formset = forms.MeasureUpdateFootnotesFormSet()
        footnotes_formset.initial = formset_footnotes
        footnotes_formset.form_kwargs = {"path": self.request.path}
        context["footnotes_formset"] = footnotes_formset
        context["footnotes"] = self.get_footnotes(context["measure"])

        conditions_initial = []
        if self.request.POST:
            conditions_initial = unprefix_formset_data(
                MEASURE_CONDITIONS_FORMSET_PREFIX,
                self.request.POST.copy(),
            )
            conditions_formset = forms.MeasureConditionsFormSet(
                self.request.POST,
                initial=conditions_initial,
                prefix=MEASURE_CONDITIONS_FORMSET_PREFIX,
            )
        else:
            conditions_formset = forms.MeasureConditionsFormSet(
                initial=conditions_initial,
                prefix=MEASURE_CONDITIONS_FORMSET_PREFIX,
            )
        conditions = self.get_conditions(context["measure"])
        form_fields = conditions_formset.form.Meta.fields
        conditions_formset.initial = []
        for condition in conditions:
            initial_dict = {}
            for field in form_fields:
                if hasattr(condition, field):
                    value = getattr(condition, field)
                    if hasattr(value, "pk"):
                        value = value.pk
                    initial_dict[field] = value

            initial_dict["applicable_duty"] = condition.duty_sentence
            initial_dict["reference_price"] = condition.reference_price_string
            initial_dict["condition_sid"] = condition.sid
            conditions_formset.initial.append(initial_dict)

        context["conditions_formset"] = conditions_formset
        return context

    def create_conditions(self, obj):
        """
        Gets condition formset from context data, loops over these forms and
        validates the data, checking for the condition_sid field in the data to
        indicate whether an existing condition is being updated or a new one
        created from scratch.

        Then deletes any existing conditions that are not being updated,
        before calling the MeasureCreationPattern.create_condition_and_components with the appropriate parser and condition data.
        """
        formset = self.get_context_data()["conditions_formset"]
        excluded_sids = []
        conditions_data = []
        workbasket = WorkBasket.current(self.request)
        existing_conditions = obj.conditions.approved_up_to_transaction(
            workbasket.get_current_transaction(self.request),
        )

        for f in formset.forms:
            f.is_valid()
            condition_data = f.cleaned_data
            # If the form has changed and "condition_sid" is in the changed data,
            # this means that the condition is preexisting and needs to updated
            # so that its dependent_measure points to the latest version of measure
            if f.has_changed() and "condition_sid" in f.changed_data:
                excluded_sids.append(f.initial["condition_sid"])
                update_type = UpdateType.UPDATE
                condition_data["version_group"] = existing_conditions.get(
                    sid=f.initial["condition_sid"],
                ).version_group
                condition_data["sid"] = f.initial["condition_sid"]
            # If changed and condition_sid not in changed_data, then this is a newly created condition
            elif f.has_changed() and "condition_sid" not in f.changed_data:
                update_type = UpdateType.CREATE

            condition_data["update_type"] = update_type
            conditions_data.append(condition_data)

        workbasket = WorkBasket.current(self.request)

        # Delete all existing conditions from the measure instance, except those that need to be updated
        for condition in existing_conditions.exclude(sid__in=excluded_sids):
            condition.new_version(
                workbasket=workbasket,
                update_type=UpdateType.DELETE,
                transaction=obj.transaction,
            )

        if conditions_data:
            measure_creation_pattern = MeasureCreationPattern(
                workbasket=workbasket,
                base_date=obj.valid_between.lower,
            )
            parser = DutySentenceParser.create(
                obj.valid_between.lower,
                component_output=models.MeasureConditionComponent,
            )

            # Loop over conditions_data, starting at 1 because component_sequence_number has to start at 1
            for component_sequence_number, condition_data in enumerate(
                conditions_data,
                start=1,
            ):
                # Create conditions and measure condition components, using instance as `dependent_measure`
                measure_creation_pattern.create_condition_and_components(
                    condition_data,
                    component_sequence_number,
                    obj,
                    parser,
                    workbasket,
                )

    def get_result_object(self, form):
        obj = super().get_result_object(form)
        form.instance = obj
        self.create_conditions(obj)
        obj = form.save(commit=False)
        return obj


class MeasureUpdate(MeasureUpdateBase):
    """UI endpoint for creating Measure UPDATE instances."""


class MeasureEditUpdate(MeasureUpdateBase):
    """UI endpoint for editing Measure UPDATE instances."""


class MeasureEditCreate(MeasureUpdateBase):
    """UI endpoint for editing Measure CREATE instances."""


class MeasureConfirmUpdate(MeasureMixin, TrackedModelDetailView):
    template_name = "common/confirm_update.jinja"


class MeasureFootnotesUpdate(View):
    """Separate post-only view for adding or removing footnotes on an existing
    measure."""

    def get_delete_key(self, footnote_key: str) -> str:
        """
        Expects a string of format 'form-0-footnote' or 'form-1-footnote' etc.

        Outputs a string of format 'form-0-DELETE' or 'form-1-DELETE' etc.
        """
        form_prefix, _ = footnote_key.rsplit("-", 1)
        return f"{form_prefix}-DELETE"

    def post(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        """
        Checks for 'remove' key in request.POST.

        If found, updates request session with PK of footnote to be removed from
        measure. If not found, updates request session with footnote pks to
        populate formset, ignoring footnotes marked for deletion in the formset.
        """
        sid = self.kwargs.get("sid")

        if "remove" in request.POST:
            request.session[f"instance_footnotes_{sid}"].remove(
                int(request.POST.get("remove")),
            )
            request.session.save()
        else:
            keys = request.POST.keys()
            footnote_keys = [
                key
                for key in keys
                if "footnote" in key and "form" in key and "auto" not in key
            ]
            request.session[f"formset_initial_{sid}"] = [
                {"footnote": request.POST[footnote]}
                for footnote in footnote_keys
                if self.get_delete_key(footnote) not in keys and request.POST[footnote]
            ]

        return HttpResponseRedirect(reverse("measure-ui-edit", args=[sid]))


class MeasureSelectionUpdate(MeasureSessionStoreMixin, View):
    def post(self, request, *args, **kwargs):
        self.session_store.clear()
        data = json.loads(request.body)
        cleaned_data = {k: v for k, v in data.items() if "selectableobject_" in k}
        selected_objects = {k: v for k, v in cleaned_data.items() if v == 1}
        self.session_store.add_items(selected_objects)
        return JsonResponse(self.session_store.data)
