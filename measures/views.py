from itertools import groupby
from operator import attrgetter
from typing import Any
from typing import Type

from crispy_forms.helper import FormHelper
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.transaction import atomic
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic.edit import FormView
from formtools.wizard.views import NamedUrlSessionWizardView
from rest_framework import viewsets
from rest_framework.reverse import reverse

from common.models import TrackedModel
from common.serializers import AutoCompleteSerializer
from common.session_store import SessionStore
from common.validators import UpdateType
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin
from common.views import TrackedModelDetailView
from measures import constants
from measures import forms
from measures.filters import MeasureFilter
from measures.filters import MeasureTypeFilterBackend
from measures.helpers import create_conditions
from measures.helpers import update_conditions
from measures.helpers import update_measure
from measures.helpers import update_measure_footnotes
from measures.models import FootnoteAssociationMeasure
from measures.models import Measure
from measures.models import MeasureConditionComponent
from measures.models import MeasureType
from measures.pagination import MeasurePaginator
from measures.parsers import DutySentenceParser
from measures.patterns import MeasureCreationPattern
from workbaskets import forms as workbasket_forms
from workbaskets.models import WorkBasket
from workbaskets.views.decorators import require_current_workbasket
from workbaskets.views.generic import CreateTaricDeleteView
from workbaskets.views.generic import CreateTaricUpdateView
from workbaskets.views.mixins import WithCurrentWorkBasket

STEP_METADATA = {
    constants.MEASURE_DETAILS: {
        "title": "Enter the basic data",
        "link_text": "Measure details",
    },
    constants.REGULATION_ID: {
        "title": "Enter the Regulation ID",
        "link_text": "Regulation ID",
    },
    constants.QUOTA_ORDER_NUMBER: {
        "title": "Enter the Quota Order Number",
        "link_text": "Quota Order Number",
    },
    constants.GEOGRAPHICAL_AREA: {
        "title": "Select the geographical area",
        "link_text": "Geographical areas",
        "info": "The measure will only apply to imports from or exports to the selected area. You can specify exclusions.",
    },
    constants.COMMODITIES: {
        "title": "Select a commodity",
        "link_text": "Commodity",
    },
    constants.DUTIES: {
        "title": "Enter the duties",
        "link_text": "Duties",
    },
    constants.ADDITIONAL_CODE: {
        "title": "Assign an additional code",
        "link_text": "Additional code",
    },
    constants.CONDITIONS: {
        "title": "Add any condition codes",
        "info": (
            "This section is optional. If there are no condition "
            "codes, select continue."
        ),
        "link_text": "Conditions",
    },
    constants.FOOTNOTES: {
        "title": "Add any footnotes",
        "info": (
            "This section is optional. If there are no footnotes, " "select continue."
        ),
        "link_text": "Footnotes",
    },
}


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

        return Measure.objects.approved_up_to_transaction(tx)


class MeasureList(MeasureMixin, FormView, TamatoListView):
    """UI endpoint for viewing and filtering Measures."""

    template_name = "measures/list.jinja"
    filterset_class = MeasureFilter
    form_class = workbasket_forms.SelectableObjectsForm
    update_type = UpdateType.UPDATE

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        page = self.paginator.get_page(self.request.GET.get("page", 1))
        kwargs["objects"] = page.object_list
        return kwargs

    @property
    def paginator(self):
        filterset_class = self.get_filterset_class()
        self.filterset = self.get_filterset(filterset_class)
        return MeasurePaginator(self.filterset.qs, per_page=10)

    def form_valid(self, form):
        store = SessionStore(
            self.request,
            "MEASURE_SELECTIONS",
        )
        # clear the store here before adding items
        # in case there was a previous form in progress that was abandoned
        store.clear()
        object_pks = {k: True for k, v in form.cleaned_data_no_prefix.items() if v}
        store.add_items(object_pks)
        url = reverse("measure-ui-edit-multiple", kwargs={"step": "start"})
        return HttpResponseRedirect(url)


class MeasuresEditWizard(
    WithCurrentWorkBasket,
    PermissionRequiredMixin,
    NamedUrlSessionWizardView,
):

    update_type = UpdateType.UPDATE
    permission_required = "common.add_trackedmodel"

    step_metadata = {
        constants.START: {
            "title": "Select the elements you want to edit",
            "link_text": "Start",
        },
        constants.END_DATES: {"title": "Edit the end dates", "link_text": "End dates"},
        constants.REGULATION_ID: STEP_METADATA[constants.REGULATION_ID],
        constants.QUOTA_ORDER_NUMBER: STEP_METADATA[constants.QUOTA_ORDER_NUMBER],
        constants.GEOGRAPHICAL_AREA: STEP_METADATA[constants.GEOGRAPHICAL_AREA],
        constants.COMMODITIES: STEP_METADATA[constants.COMMODITIES],
        constants.DUTIES: STEP_METADATA[constants.DUTIES],
        constants.ADDITIONAL_CODE: STEP_METADATA[constants.ADDITIONAL_CODE],
        constants.CONDITIONS: STEP_METADATA[constants.CONDITIONS],
        constants.FOOTNOTES: STEP_METADATA[constants.FOOTNOTES],
        constants.SUMMARY: {
            "title": "Review your changes",
            "link_text": "Summary",
        },
        constants.COMPLETE: {
            "title": "Finished",
            "link_text": "Success",
        },
    }

    form_list = [
        (constants.START, forms.MeasuresEditStartForm),
        (constants.END_DATES, forms.MeasureEndDateForm),
        (constants.REGULATION_ID, forms.MeasureRegulationIdForm),
        (constants.QUOTA_ORDER_NUMBER, forms.MeasureQuotaOrderNumberForm),
        (constants.GEOGRAPHICAL_AREA, forms.MeasureGeographicalAreaForm),
        (constants.DUTIES, forms.MeasureDutiesMultipleEditForm),
        (constants.ADDITIONAL_CODE, forms.MeasureAdditionalCodeForm),
        (constants.CONDITIONS, forms.MeasureConditionsEditWizardStepFormSet),
        (constants.FOOTNOTES, forms.MeasureFootnotesFormSet),
        (constants.SUMMARY, forms.MeasureReviewForm),
    ]

    templates = {
        constants.START: "measures/edit-multiple-start.jinja",
        constants.END_DATES: "measures/edit-wizard-step.jinja",
        constants.REGULATION_ID: "measures/edit-wizard-step.jinja",
        constants.QUOTA_ORDER_NUMBER: "measures/edit-wizard-step.jinja",
        constants.GEOGRAPHICAL_AREA: "measures/edit-wizard-step.jinja",
        constants.DUTIES: "measures/edit-wizard-step.jinja",
        constants.ADDITIONAL_CODE: "measures/edit-wizard-step.jinja",
        constants.CONDITIONS: "measures/create-formset.jinja",
        constants.FOOTNOTES: "measures/create-formset.jinja",
        constants.SUMMARY: "measures/edit-review.jinja",
        constants.COMPLETE: "measures/confirm-edit-multiple.jinja",
    }

    def get(self, *args, **kwargs):
        if not self.measures:
            return redirect("measure-ui-list")
        return super().get(*args, **kwargs)

    def get_template_names(self):
        return self.templates.get(
            self.steps.current,
            "measures/edit-wizard-step.jinja",
        )

    @property
    def _session_store(self):
        """Get the current user's SessionStore containing ids of the measures
        that have been selected for editing."""

        return SessionStore(
            self.request,
            "MEASURE_SELECTIONS",
        )

    @property
    def measures(self):
        return Measure.objects.filter(pk__in=self._session_store.data.keys())

    def get_form_kwargs(self, step):
        kwargs = {}
        if step == constants.DUTIES:
            # duty sentence validation requires the measure start date so pass it to form kwargs here
            measure_start_dates = [
                measure.valid_between.lower for measure in self.measures
            ]
            # commodities/duties step is a formset which expects form_kwargs to pass kwargs to its child forms
            kwargs["measure_start_dates"] = measure_start_dates
        elif step == constants.CONDITIONS:
            # duty sentence validation requires the measure start date so pass it to form kwargs here
            measure_start_dates = [
                measure.valid_between.lower for measure in self.measures
            ]
            # commodities/duties step is a formset which expects form_kwargs to pass kwargs to its child forms
            kwargs["form_kwargs"] = {"measure_start_dates": measure_start_dates}

        return kwargs

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        context["step_metadata"] = self.step_metadata
        if form:
            context["form"].is_bound = False
        context["no_form_tags"] = FormHelper()
        context["no_form_tags"].form_tag = False
        context["measures"] = self.measures
        return context

    def done(self, form_list, **kwargs):
        cleaned_data = self.get_all_cleaned_data()
        current_workbasket = WorkBasket.current(self.request)
        tx = WorkBasket.get_current_transaction(self.request)

        edited_measures = []

        footnote_pks = [
            item["footnote"].pk
            for item in cleaned_data.get("formset-footnotes", [])
            if not item.get("DELETE")
        ]
        conditions_data = cleaned_data.get("formset-conditions", [])
        for condition in conditions_data:
            condition["update_type"] = UpdateType.CREATE

        for measure in self.measures:
            defaults = {"generating_regulation": measure.generating_regulation}
            new_measure = update_measure(
                measure,
                tx,
                current_workbasket,
                cleaned_data,
                defaults,
            )
            create_conditions(
                measure,
                new_measure.transaction,
                current_workbasket,
                conditions_data,
            )
            update_measure_footnotes(
                new_measure,
                new_measure.transaction,
                current_workbasket,
                footnote_pks,
            )

            edited_measures.append(measure)

        context = self.get_context_data(
            form=None,
            edited_measures=edited_measures,
            **kwargs,
        )

        return render(self.request, "measures/confirm-edit-multiple.jinja", context)


class MeasureDetail(MeasureMixin, TrackedModelDetailView):
    model = Measure
    template_name = "measures/detail.jinja"
    queryset = Measure.objects.latest_approved()

    def get_context_data(self, **kwargs: Any):
        conditions = (
            self.object.conditions.current()
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
        context["has_conditions"] = bool(len(conditions))
        return context


@method_decorator(require_current_workbasket, name="dispatch")
class MeasureCreateWizard(
    NamedUrlSessionWizardView,
):
    storage_name = "measures.wizard.MeasureCreateSessionStorage"
    step_metadata = {
        constants.START: {
            "title": "Create a new measure",
            "link_text": "Start",
        },
        constants.MEASURE_DETAILS: STEP_METADATA[constants.MEASURE_DETAILS],
        constants.REGULATION_ID: STEP_METADATA[constants.REGULATION_ID],
        constants.QUOTA_ORDER_NUMBER: STEP_METADATA[constants.QUOTA_ORDER_NUMBER],
        constants.GEOGRAPHICAL_AREA: STEP_METADATA[constants.GEOGRAPHICAL_AREA],
        constants.COMMODITIES: STEP_METADATA[constants.COMMODITIES],
        constants.ADDITIONAL_CODE: STEP_METADATA[constants.ADDITIONAL_CODE],
        constants.CONDITIONS: STEP_METADATA[constants.CONDITIONS],
        constants.FOOTNOTES: STEP_METADATA[constants.FOOTNOTES],
        constants.SUMMARY: {
            "title": "Review your measure",
            "link_text": "Summary",
        },
        constants.COMPLETE: {
            "title": "Finished",
            "link_text": "Success",
        },
    }

    form_list = [
        (constants.START, forms.MeasureCreateStartForm),
        (constants.MEASURE_DETAILS, forms.MeasureDetailsForm),
        (constants.REGULATION_ID, forms.MeasureRegulationIdForm),
        (constants.QUOTA_ORDER_NUMBER, forms.MeasureQuotaOrderNumberForm),
        (constants.GEOGRAPHICAL_AREA, forms.MeasureGeographicalAreaForm),
        (constants.COMMODITIES, forms.MeasureCommodityAndDutiesFormSet),
        (constants.ADDITIONAL_CODE, forms.MeasureAdditionalCodeForm),
        (constants.CONDITIONS, forms.MeasureConditionsWizardStepFormSet),
        (constants.FOOTNOTES, forms.MeasureFootnotesFormSet),
        (constants.SUMMARY, forms.MeasureReviewForm),
    ]

    templates = {
        constants.START: "measures/create-start.jinja",
        constants.MEASURE_DETAILS: "measures/create-wizard-step.jinja",
        constants.REGULATION_ID: "measures/create-wizard-step.jinja",
        constants.QUOTA_ORDER_NUMBER: "measures/create-wizard-step.jinja",
        constants.GEOGRAPHICAL_AREA: "measures/create-wizard-step.jinja",
        constants.COMMODITIES: "measures/create-formset.jinja",
        constants.ADDITIONAL_CODE: "measures/create-wizard-step.jinja",
        constants.CONDITIONS: "measures/create-formset.jinja",
        constants.FOOTNOTES: "measures/create-formset.jinja",
        constants.SUMMARY: "measures/create-review.jinja",
        constants.COMPLETE: "measures/confirm-create-multiple.jinja",
    }

    @atomic
    def create_measures(self, data):
        """Returns a list of the created measures."""
        measure_start_date = data["valid_between"].lower
        workbasket = WorkBasket.current(self.request)
        measure_creation_pattern = MeasureCreationPattern(
            workbasket=workbasket,
            base_date=measure_start_date,
            defaults={
                "generating_regulation": data["generating_regulation"],
            },
        )

        measures_data = []

        for commodity_data in data.get("formset-commodities", []):
            if not commodity_data.get("DELETE"):
                for geo_area in data["geo_area_list"]:

                    measure_data = {
                        "measure_type": data["measure_type"],
                        "geographical_area": geo_area,
                        "exclusions": data.get("geo_area_exclusions", None) or [],
                        "goods_nomenclature": commodity_data["commodity"],
                        "additional_code": data["additional_code"],
                        "order_number": data["order_number"],
                        "validity_start": measure_start_date,
                        "validity_end": data["valid_between"].upper,
                        "footnotes": [
                            item["footnote"]
                            for item in data.get("formset-footnotes", [])
                            if not item.get("DELETE")
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
                if not condition_data.get("DELETE"):

                    measure_creation_pattern.create_condition_and_components(
                        condition_data,
                        component_sequence_number,
                        measure,
                        parser,
                        workbasket,
                    )

            created_measures.append(measure)

        return created_measures

    def done(self, form_list, **kwargs):
        cleaned_data = self.get_all_cleaned_data()

        created_measures = self.create_measures(cleaned_data)
        created_measures[0].transaction.workbasket.save_to_session(self.request.session)

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

    def get_form_kwargs(self, step):
        kwargs = {}
        if step == constants.COMMODITIES or step == constants.CONDITIONS:
            # duty sentence validation requires the measure start date so pass it to form kwargs here
            valid_between = self.get_cleaned_data_for_step(
                constants.MEASURE_DETAILS,
            ).get(
                "valid_between",
            )
            # commodities/duties step is a formset which expects form_kwargs to pass kwargs to its child forms
            kwargs["form_kwargs"] = {"measure_start_date": valid_between.lower}

        return kwargs

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
            "measures/measure-wizard-step.jinja",
        )


class MeasureUpdate(
    MeasureMixin,
    TrackedModelDetailMixin,
    CreateTaricUpdateView,
):
    form_class = forms.MeasureForm
    permission_required = "common.change_trackedmodel"
    template_name = "measures/edit.jinja"
    queryset = Measure.objects.all()

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
            footnoted_measure__sid=measure.sid,
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

        if self.request.POST:
            conditions_formset = forms.MeasureConditionsFormSet(self.request.POST)
        else:
            conditions_formset = forms.MeasureConditionsFormSet()
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

            initial_dict["applicable_duty"] = condition.condition_string
            initial_dict["reference_price"] = condition.reference_price_string
            initial_dict["condition_sid"] = condition.sid
            conditions_formset.initial.append(initial_dict)

        context["conditions_formset"] = conditions_formset
        return context

    def get_result_object(self, form):
        instance = super().get_result_object(form)
        form.instance = instance
        current_workbasket = WorkBasket.current(self.request)
        current_workbasket.get_current_transaction(self.request)
        formset = self.get_context_data()["conditions_formset"]
        new_measure = form.save(commit=False)
        update_conditions(
            instance,
            new_measure.transaction,
            current_workbasket,
            formset,
        )

        return instance


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
    CreateTaricDeleteView,
):
    form_class = forms.MeasureDeleteForm
    success_path = "list"
