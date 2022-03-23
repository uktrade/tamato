from itertools import groupby
from operator import attrgetter
from typing import Any
from typing import Type

from crispy_forms.helper import FormHelper
from django.db.transaction import atomic
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from formtools.wizard.views import NamedUrlSessionWizardView
from rest_framework import viewsets
from rest_framework.reverse import reverse

from common.models import TrackedModel
from common.serializers import AutoCompleteSerializer
from common.validators import UpdateType
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin
from common.views import TrackedModelDetailView
from measures import forms
from measures.filters import MeasureFilter
from measures.filters import MeasureTypeFilterBackend
from measures.models import FootnoteAssociationMeasure
from measures.models import Measure
from measures.models import MeasureCondition
from measures.models import MeasureConditionComponent
from measures.models import MeasureType
from measures.pagination import MeasurePaginator
from measures.parsers import DutySentenceParser
from measures.patterns import MeasureCreationPattern
from workbaskets.models import WorkBasket
from workbaskets.views.decorators import require_current_workbasket
from workbaskets.views.generic import DraftDeleteView
from workbaskets.views.generic import DraftUpdateView


class MeasureTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows measure types to be viewed."""

    serializer_class = AutoCompleteSerializer
    filter_backends = [MeasureTypeFilterBackend]

    def get_queryset(self):
        tx = WorkBasket.get_current_transaction(self.request)
        return MeasureType.objects.approved_up_to_transaction(tx).order_by(
            "description",
        )


class MeasureMixin:
    model: Type[TrackedModel] = Measure

    def get_queryset(self):
        tx = WorkBasket.get_current_transaction(self.request)

        return Measure.objects.with_duty_sentence().approved_up_to_transaction(tx)


class MeasureList(MeasureMixin, TamatoListView):
    """UI endpoint for viewing and filtering Measures."""

    paginator_class = MeasurePaginator
    template_name = "measures/list.jinja"
    filterset_class = MeasureFilter


class MeasureDetail(MeasureMixin, TrackedModelDetailView):
    model = Measure
    template_name = "measures/detail.jinja"
    queryset = Measure.objects.with_duty_sentence().latest_approved()

    def get_context_data(self, **kwargs: Any):
        conditions = (
            self.object.conditions.current()
            .with_duty_sentence()
            .prefetch_related(
                "condition_code",
                "required_certificate",
                "required_certificate__certificate_type",
                "condition_measurement__measurement_unit",
                "condition_measurement__measurement_unit_qualifier",
                "action",
            )
            .order_by("condition_code__code", "component_sequence_number")
        )
        condition_groups = groupby(conditions, attrgetter("condition_code"))

        context = super().get_context_data(**kwargs)
        context["condition_groups"] = condition_groups
        return context


@method_decorator(require_current_workbasket, name="dispatch")
class MeasureCreateWizard(
    NamedUrlSessionWizardView,
):
    storage_name = "measures.wizard.MeasureCreateSessionStorage"

    START = "start"
    MEASURE_DETAILS = "measure_details"
    COMMODITIES = "commodities"
    ADDITIONAL_CODE = "additional_code"
    CONDITIONS = "conditions"
    FOOTNOTES = "footnotes"
    SUMMARY = "summary"
    COMPLETE = "complete"

    form_list = [
        (START, forms.MeasureCreateStartForm),
        (MEASURE_DETAILS, forms.MeasureDetailsForm),
        (COMMODITIES, forms.MeasureCommodityAndDutiesFormSet),
        (ADDITIONAL_CODE, forms.MeasureAdditionalCodeForm),
        (CONDITIONS, forms.MeasureConditionsFormSet),
        (FOOTNOTES, forms.MeasureFootnotesFormSet),
        (SUMMARY, forms.MeasureReviewForm),
    ]

    templates = {
        START: "measures/create-start.jinja",
        MEASURE_DETAILS: "measures/create-wizard-step.jinja",
        COMMODITIES: "measures/create-formset.jinja",
        ADDITIONAL_CODE: "measures/create-wizard-step.jinja",
        CONDITIONS: "measures/create-formset.jinja",
        FOOTNOTES: "measures/create-formset.jinja",
        SUMMARY: "measures/create-review.jinja",
        COMPLETE: "measures/confirm-create-multiple.jinja",
    }

    step_metadata = {
        START: {
            "title": "Create a new measure",
            "link_text": "Start",
        },
        MEASURE_DETAILS: {
            "title": "Enter the basic data",
            "link_text": "Measure details",
        },
        COMMODITIES: {
            "title": "Select commodities and enter the duties",
            "link_text": "Commodities and duties",
        },
        ADDITIONAL_CODE: {
            "title": "Assign an additional code",
            "link_text": "Additional code",
        },
        CONDITIONS: {
            "title": "Add any condition codes",
            "info": (
                "This section is optional. If there are no condition "
                "codes, select continue."
            ),
            "link_text": "Conditions",
        },
        FOOTNOTES: {
            "title": "Add any footnotes",
            "info": (
                "This section is optional. If there are no footnotes, "
                "select continue."
            ),
            "link_text": "Footnotes",
        },
        SUMMARY: {
            "title": "Review your measure",
            "link_text": "Summary",
        },
        COMPLETE: {
            "title": "Finished",
            "link_text": "Success",
        },
    }

    @atomic
    def create_measures(self, data):
        """Returns a list of the created measures."""
        measure_start_date = data["valid_between"].lower

        measure_creation_pattern = MeasureCreationPattern(
            workbasket=WorkBasket.current(self.request),
            base_date=measure_start_date,
            defaults={
                "generating_regulation": data["generating_regulation"],
            },
        )

        measures_data = []

        for commodity_data in data.get("formset-commodities", []):
            if not commodity_data["DELETE"]:

                measure_data = {
                    "measure_type": data["measure_type"],
                    "geographical_area": data["geographical_area"],
                    "exclusions": data.get("geo_area_exclusions", []),
                    "goods_nomenclature": commodity_data["commodity"],
                    "additional_code": data["additional_code"],
                    "order_number": data["order_number"],
                    "validity_start": measure_start_date,
                    "validity_end": data["valid_between"].upper,
                    "footnotes": [
                        item["footnote"]
                        for item in data.get("formset-footnotes", [])
                        if not item["DELETE"]
                    ],
                    # condition_sentence here, or handle separately and duty_sentence after?
                    "duty_sentence": commodity_data["duties"],
                }

                measures_data.append(measure_data)

        created_measures = []

        for measure_data in measures_data:
            measure = measure_creation_pattern.create(**measure_data)
            parser = DutySentenceParser.get(
                measure.valid_between.lower,
                component_output=MeasureConditionComponent,
            )
            for component_sequence_number, condition_data in enumerate(
                data.get("formset-conditions", []),
                start=1,
            ):
                if not condition_data["DELETE"]:

                    condition = MeasureCondition(
                        sid=measure_creation_pattern.measure_condition_sid_counter(),
                        component_sequence_number=component_sequence_number,
                        dependent_measure=measure,
                        update_type=UpdateType.CREATE,
                        transaction=measure.transaction,
                        duty_amount=condition_data.get("duty_amount"),
                        condition_code=condition_data["condition_code"],
                        action=condition_data.get("action"),
                        required_certificate=condition_data.get("required_certificate"),
                        monetary_unit=condition_data.get("monetary_unit"),
                        condition_measurement=condition_data.get(
                            "condition_measurement",
                        ),
                    )
                    condition.clean()
                    condition.save()

                    # XXX the design doesn't show whether the condition duty_amount field
                    # should handle duty_expression, monetary_unit or measurements, so this
                    # code assumes some sensible(?) defaults
                    if condition_data.get("applicable_duty"):
                        components = parser.parse(condition_data["applicable_duty"])
                        for c in components:
                            c.condition = condition
                            c.transaction = condition.transaction
                            c.update_type = UpdateType.CREATE
                            c.save()

            created_measures.append(measure)

        return created_measures

    def done(self, form_list, **kwargs):
        cleaned_data = self.get_all_cleaned_data()

        created_measures = self.create_measures(cleaned_data)

        context = self.get_context_data(
            form=None,
            created_measures=created_measures,
            **kwargs,
        )

        return render(self.request, "measures/confirm-create-multiple.jinja", context)

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        context["step_metadata"] = self.step_metadata
        if form:
            context["form"].is_bound = False
        context["no_form_tags"] = FormHelper()
        context["no_form_tags"].form_tag = False
        return context

    def get_form_initial(self, step):
        current_step = self.storage.current_step
        initial_data = super().get_form_initial(step)

        if (current_step, step) == ("duties", "duties"):
            # At each step get_form_initial is called for every step, avoid a loop
            details_data = self.get_cleaned_data_for_step("measure_details")

            # Data may not be present if the user has skipped forward.
            valid_between = details_data.get("valid_between") if details_data else None

            # The user may go through the wizard in any order, handle the case where there is no
            # date by defaulting to None (no lower bound)
            measure_start_date = valid_between.lower if valid_between else None
            return {
                "measure_start_date": measure_start_date,
                **initial_data,
            }

        return initial_data

    def get_form(self, step=None, data=None, files=None):
        form = super().get_form(step, data, files)
        tx = WorkBasket.get_current_transaction(self.request)
        forms = [form]
        if hasattr(form, "forms"):
            forms = form.forms
        for f in forms:
            if hasattr(f, "fields"):
                for field in f.fields.values():
                    if hasattr(field, "queryset"):
                        field.queryset = field.queryset.approved_up_to_transaction(tx)

        form.is_valid()
        if hasattr(form, "cleaned_data"):
            form.initial = form.cleaned_data

        return form

    def get_template_names(self):
        return self.templates.get(
            self.steps.current,
            "measures/create-wizard-step.jinja",
        )


class MeasureUpdate(
    MeasureMixin,
    TrackedModelDetailMixin,
    DraftUpdateView,
):
    form_class = forms.MeasureForm
    permission_required = "common.change_trackedmodel"
    template_name = "measures/edit.jinja"
    queryset = Measure.objects.with_duty_sentence()

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
        associations = FootnoteAssociationMeasure.objects.approved_up_to_transaction(
            tx,
        ).filter(
            footnoted_measure=measure,
        )

        return [a.associated_footnote for a in associations]

    def get_conditions(self, measure):
        tx = WorkBasket.get_current_transaction(self.request)
        return (
            measure.conditions.with_duty_sentence()
            .with_reference_price_string()
            .approved_up_to_transaction(tx)
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        initial = self.request.session.get(
            f"formset_initial_{self.kwargs.get('sid')}",
            [],
        )
        formset = forms.MeasureUpdateFootnotesFormSet()
        formset.initial = initial
        formset.form_kwargs = {"path": self.request.path}
        context["formset"] = formset
        context["no_form_tags"] = FormHelper()
        context["no_form_tags"].form_tag = False
        context["footnotes"] = self.get_footnotes(context["measure"])

        conditions_formset = forms.MeasureConditionsFormSet()
        conditions = self.get_conditions(context["measure"])
        form_fields = conditions_formset.form.Meta.fields
        conditions_formset.initial = []
        for condition in conditions:
            initial_dict = {}
            for field in form_fields:
                if hasattr(condition, field):
                    initial_dict[field] = getattr(condition, field)

            initial_dict["applicable_duty"] = condition.condition_string
            initial_dict["reference_price"] = condition.reference_price_string
            conditions_formset.initial.append(initial_dict)

        context["conditions_formset"] = conditions_formset
        return context

    def get_result_object(self, form):
        obj = super().get_result_object(form)
        form.instance = obj
        form.save(commit=False)

        return obj


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


class MeasureDelete(
    MeasureMixin,
    TrackedModelDetailMixin,
    DraftDeleteView,
):
    form_class = forms.MeasureDeleteForm
    success_path = "list"
