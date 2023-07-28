import datetime
import json
from itertools import groupby
from operator import attrgetter
from typing import Any
from typing import Type
from urllib.parse import urlencode

from crispy_forms.helper import FormHelper
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.transaction import atomic
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.http import JsonResponse
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView
from django.views.generic.list import ListView
from django_filters.views import FilterView
from formtools.wizard.views import NamedUrlSessionWizardView
from rest_framework import viewsets
from rest_framework.reverse import reverse

from common.forms import unprefix_formset_data
from common.models import TrackedModel
from common.serializers import AutoCompleteSerializer
from common.util import TaricDateRange
from common.validators import UpdateType
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin
from common.views import TrackedModelDetailView
from measures import forms
from measures.constants import START
from measures.constants import MeasureEditSteps
from measures.filters import MeasureFilter
from measures.filters import MeasureTypeFilterBackend
from measures.forms import MEASURE_CONDITIONS_FORMSET_PREFIX
from measures.models import FootnoteAssociationMeasure
from measures.models import Measure
from measures.models import MeasureActionPair
from measures.models import MeasureConditionComponent
from measures.models import MeasureType
from measures.pagination import MeasurePaginator
from measures.parsers import DutySentenceParser
from measures.patterns import MeasureCreationPattern
from measures.util import diff_components
from workbaskets.forms import SelectableObjectsForm
from workbaskets.models import WorkBasket
from workbaskets.session_store import SessionStore
from workbaskets.views.decorators import require_current_workbasket
from workbaskets.views.generic import CreateTaricDeleteView
from workbaskets.views.generic import CreateTaricUpdateView


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
        return Measure.objects.filter(pk__in=self.measure_selections)


class MeasureSearch(FilterView):
    """
    UI endpoint for filtering Measures.

    Does not list any measures. Redirects to MeasureList on form submit.
    """

    template_name = "measures/search.jinja"
    filterset_class = MeasureFilter

    def form_valid(self, form):
        return HttpResponseRedirect(reverse("measure-ui-list"))


class MeasureList(MeasureSelectionMixin, MeasureMixin, FormView, TamatoListView):
    """UI endpoint for viewing and filtering Measures."""

    template_name = "measures/list.jinja"
    filterset_class = MeasureFilter
    form_class = SelectableObjectsForm

    def dispatch(self, *args, **kwargs):
        if not self.request.GET:
            return HttpResponseRedirect(reverse("measure-ui-search"))
        return super().dispatch(*args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        page = self.paginator.get_page(self.request.GET.get("page", 1))
        kwargs["objects"] = page.object_list
        return kwargs

    @property
    def paginator(self):
        filterset_class = self.get_filterset_class()
        self.filterset = self.get_filterset(filterset_class)
        return MeasurePaginator(self.filterset.qs, per_page=20)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        measure_selections = [
            SelectableObjectsForm.object_id_from_field_name(name)
            for name in self.measure_selections
        ]
        context["measure_selections"] = Measure.objects.filter(
            pk__in=measure_selections,
        )
        return context

    def get_initial(self):
        return {**self.session_store.data}

    def form_valid(self, form):
        if form.data["form-action"] == "remove-selected":
            url = reverse("measure-ui-delete-multiple")
        elif form.data["form-action"] == "edit-selected":
            url = reverse("measure-ui-edit-multiple")
        elif form.data["form-action"] == "persist-selection":
            # keep selections from other pages. only update newly selected/removed measures from the current page
            selected_objects = {k: v for k, v in form.cleaned_data.items() if v}

            # clear this page from the session
            self.session_store.remove_items(form.cleaned_data)

            # then add the selected items
            self.session_store.add_items(selected_objects)

            params = urlencode(self.request.GET)
            url = f"{reverse('measure-ui-list')}?{params}"
        else:
            url = reverse("measure-ui-list")

        return HttpResponseRedirect(url)


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
class MeasureEditWizard(
    PermissionRequiredMixin,
    MeasureSelectionQuerysetMixin,
    NamedUrlSessionWizardView,
):
    """
    Multipart form wizard for editing multiple measures.

    https://django-formtools.readthedocs.io/en/latest/wizard.html
    """

    storage_name = "measures.wizard.MeasureEditSessionStorage"
    permission_required = ["common.change_trackedmodel"]

    form_list = [
        (START, forms.MeasuresEditFieldsForm),
        (MeasureEditSteps.START_DATE, forms.MeasureStartDateForm),
        (MeasureEditSteps.END_DATE, forms.MeasureEndDateForm),
        (MeasureEditSteps.QUOTA_ORDER_NUMBER, forms.MeasureQuotaOrderNumberForm),
        (MeasureEditSteps.REGULATION, forms.MeasureRegulationForm),
        (MeasureEditSteps.DUTIES, forms.MeasureDutiesForm),
    ]

    templates = {
        START: "measures/edit-multiple-start.jinja",
    }

    step_metadata = {
        START: {
            "title": "Edit measures",
        },
        MeasureEditSteps.START_DATE: {
            "title": "Edit the start date",
        },
        MeasureEditSteps.END_DATE: {
            "title": "Edit the end date",
        },
        MeasureEditSteps.REGULATION: {
            "title": "Edit the regulation",
        },
        MeasureEditSteps.QUOTA_ORDER_NUMBER: {
            "title": "Edit the quota order number",
            "link_text": "Quota order number",
        },
        MeasureEditSteps.DUTIES: {
            "title": "Edit the duties",
        },
    }

    def get_template_names(self):
        return self.templates.get(
            self.steps.current,
            "measures/edit-wizard-step.jinja",
        )

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        context["step_metadata"] = self.step_metadata
        if form:
            context["form"].is_bound = False
        context["no_form_tags"] = FormHelper()
        context["no_form_tags"].form_tag = False
        context["measures"] = self.get_queryset()
        return context

    def get_form_kwargs(self, step):
        kwargs = {}
        if step not in [START, MeasureEditSteps.QUOTA_ORDER_NUMBER]:
            kwargs["selected_measures"] = self.get_queryset()

        if step == MeasureEditSteps.DUTIES:
            start_date = (
                self.get_cleaned_data_for_step(MeasureEditSteps.START_DATE).get(
                    "start_date",
                )
                if self.get_cleaned_data_for_step(MeasureEditSteps.START_DATE)
                else None
            )
            kwargs["measures_start_date"] = start_date

        return kwargs

    def done(self, form_list, **kwargs):
        cleaned_data = self.get_all_cleaned_data()
        selected_measures = self.get_queryset()
        workbasket = WorkBasket.current(self.request)
        new_start_date = None
        new_end_date = None
        if cleaned_data.get("start_date"):
            new_start_date = datetime.date(
                cleaned_data["start_date"].year,
                cleaned_data["start_date"].month,
                cleaned_data["start_date"].day,
            )
        if cleaned_data.get("end_date"):
            new_end_date = datetime.date(
                cleaned_data["end_date"].year,
                cleaned_data["end_date"].month,
                cleaned_data["end_date"].day,
            )
        new_quota_order_number = cleaned_data.get("order_number", None)
        new_generating_regulation = cleaned_data.get("generating_regulation", None)
        new_duties = cleaned_data.get("duties", None)
        for measure in selected_measures:
            new_measure = measure.new_version(
                workbasket=workbasket,
                update_type=UpdateType.UPDATE,
                valid_between=TaricDateRange(
                    lower=new_start_date
                    if new_start_date
                    else measure.valid_between.lower,
                    upper=new_end_date if new_end_date else measure.valid_between.upper,
                ),
                order_number=new_quota_order_number
                if new_quota_order_number
                else measure.order_number,
                generating_regulation=new_generating_regulation
                if new_generating_regulation
                else measure.generating_regulation,
            )
            if new_duties:
                diff_components(
                    instance=new_measure,
                    duty_sentence=new_duties,
                    start_date=new_measure.valid_between.lower,
                    workbasket=workbasket,
                    transaction=workbasket.current_transaction,
                )
            footnote_associations = FootnoteAssociationMeasure.objects.current().filter(
                footnoted_measure=measure,
            )
            for fa in footnote_associations:
                fa.new_version(
                    workbasket=workbasket,
                    update_type=UpdateType.UPDATE,
                    footnoted_measure=new_measure,
                )
            self.session_store.clear()

        return redirect(reverse("workbaskets:review-workbasket"))


@method_decorator(require_current_workbasket, name="dispatch")
class MeasureCreateWizard(
    PermissionRequiredMixin,
    NamedUrlSessionWizardView,
):
    """
    Multipart form wizard for creating a single measure.

    https://django-formtools.readthedocs.io/en/latest/wizard.html
    """

    storage_name = "measures.wizard.MeasureCreateSessionStorage"

    permission_required = ["common.add_trackedmodel"]

    START = "start"
    MEASURE_DETAILS = "measure_details"
    REGULATION_ID = "regulation_id"
    QUOTA_ORDER_NUMBER = "quota_order_number"
    GEOGRAPHICAL_AREA = "geographical_area"
    COMMODITIES = "commodities"
    ADDITIONAL_CODE = "additional_code"
    CONDITIONS = "conditions"
    FOOTNOTES = "footnotes"
    SUMMARY = "summary"
    COMPLETE = "complete"

    form_list = [
        (START, forms.MeasureCreateStartForm),
        (MEASURE_DETAILS, forms.MeasureDetailsForm),
        (REGULATION_ID, forms.MeasureRegulationIdForm),
        (QUOTA_ORDER_NUMBER, forms.MeasureQuotaOrderNumberForm),
        (GEOGRAPHICAL_AREA, forms.MeasureGeographicalAreaForm),
        (COMMODITIES, forms.MeasureCommodityAndDutiesFormSet),
        (ADDITIONAL_CODE, forms.MeasureAdditionalCodeForm),
        (CONDITIONS, forms.MeasureConditionsWizardStepFormSet),
        (FOOTNOTES, forms.MeasureFootnotesFormSet),
        (SUMMARY, forms.MeasureReviewForm),
    ]

    templates = {
        START: "measures/create-start.jinja",
        MEASURE_DETAILS: "measures/create-wizard-step.jinja",
        REGULATION_ID: "measures/create-wizard-step.jinja",
        QUOTA_ORDER_NUMBER: "measures/create-wizard-step.jinja",
        GEOGRAPHICAL_AREA: "measures/create-wizard-step.jinja",
        COMMODITIES: "measures/create-comm-codes-formset.jinja",
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
        REGULATION_ID: {
            "title": "Enter the regulation ID",
            "link_text": "Regulation ID",
        },
        QUOTA_ORDER_NUMBER: {
            "title": "Enter a quota order number (optional)",
            "link_text": "Quota order number",
        },
        GEOGRAPHICAL_AREA: {
            "title": "Select the geographical area",
            "link_text": "Geographical areas",
        },
        COMMODITIES: {
            "title": "Select commodities and enter the duties",
            "link_text": "Commodities and duties",
        },
        ADDITIONAL_CODE: {
            "title": "Assign an additional code (optional)",
            "link_text": "Additional code",
        },
        CONDITIONS: {
            "title": "Add any condition codes (optional)",
            "link_text": "Conditions",
            "info": """Add conditions and resulting actions to your measure(s). If a condition group is not met, the opposite action will be applied. 
            The opposite action is created automatically.
            """,
        },
        FOOTNOTES: {
            "title": "Add any footnotes (optional)",
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

    @property
    def workbasket(self) -> WorkBasket:
        return WorkBasket.current(self.request)

    def create_measure_conditions(
        self,
        data,
        measure: Measure,
        measure_creation_pattern: MeasureCreationPattern,
        parser: DutySentenceParser,
    ):
        """
        Create's measure conditions, components, and their corresponding negative actions
        Args:
            data: object with the form wizards data
            measure: Current created measure
            measure_creation_pattern: MeasureCreationPattern
            parser: DutySentenceParser
        Returns:
            None
        """
        # component number not tied to position in formset as negative conditions are auto generated
        component_sequence_number = 1
        for index, condition_data in enumerate(
            data.get("formset-conditions", []),
        ):
            if not condition_data.get("DELETE"):
                # creates a list of tuples with condition and action code
                # this will be used to create the corresponding negative action
                measure_creation_pattern.create_condition_and_components(
                    condition_data,
                    component_sequence_number,
                    measure,
                    parser,
                    self.workbasket,
                )

                # set next code unless last item set None
                next_condition_code = (
                    data["formset-conditions"][index + 1]["condition_code"]
                    if (index + 1 < len(data["formset-conditions"]))
                    else None
                )
                # corresponding negative action to the postive one. None if the action code has no pair
                action_pair = MeasureActionPair.objects.filter(
                    positive_action__code=condition_data.get("action").code,
                ).first()

                negative_action = None

                if action_pair:
                    negative_action = action_pair.negative_action
                elif (
                    measure.measure_type
                    in measure_creation_pattern.autonomous_tariff_suspension_use_measure_types
                    and condition_data.get("action").code == "01"
                ):
                    """If measure type is an automatic suspension and an action
                    code 01 is selected then the negative action of code 07
                    (measure not applicable)is used."""
                    negative_action = measure_creation_pattern.measure_not_applicable

                # if the next condition code is different create the negative action for the current condition
                # only create a negative action if the action has a negative pair
                if (
                    negative_action
                    and data["formset-conditions"][index]["condition_code"]
                    != next_condition_code
                ):
                    component_sequence_number += 1
                    measure_creation_pattern.create_condition_and_components(
                        {
                            "condition_code": condition_data.get("condition_code"),
                            "duty_amount": None,
                            "required_certificate": None,
                            # corresponding negative action to the postive one.
                            "action": negative_action,
                            "DELETE": False,
                        },
                        component_sequence_number,
                        measure,
                        parser,
                        self.workbasket,
                    )

            # deletes also increment or well did when using the enumerated index
            component_sequence_number += 1

    @atomic
    def create_measures(self, data):
        """Returns a list of the created measures."""
        measure_start_date = data["valid_between"].lower

        measure_creation_pattern = MeasureCreationPattern(
            workbasket=self.workbasket,
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

        parser = DutySentenceParser.create(
            measure_start_date,
            component_output=MeasureConditionComponent,
        )

        created_measures = []

        for measure_data in measures_data:
            # creates measure in DB
            measure = measure_creation_pattern.create(**measure_data)
            self.create_measure_conditions(
                data,
                measure,
                measure_creation_pattern,
                parser,
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
        `get_form_kwargs()` and qtemplate for summary page) to avoid revalidating forms unnecessarily.
        """
        self.cleaned_data = getattr(self, "cleaned_data", {})
        if step in self.cleaned_data:
            return self.cleaned_data[step]

        self.cleaned_data[step] = super().get_cleaned_data_for_step(step)
        return self.cleaned_data[step]

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
        if step == self.COMMODITIES:
            measure_start_date = None
            measure_type = None
            min_commodity_count = 0
            measure_details = self.get_cleaned_data_for_step(self.MEASURE_DETAILS)
            if measure_details:
                measure_start_date = measure_details.get("valid_between").lower
                measure_type = measure_type = measure_details.get("measure_type")
                min_commodity_count = measure_details.get("min_commodity_count")
            # Kwargs expected by formset
            kwargs.update(
                {
                    "min_commodity_count": min_commodity_count,
                    "measure_start_date": measure_start_date,
                },
            )
            # Kwargs expected by forms in formset
            kwargs["form_kwargs"] = {
                "measure_type": measure_type,
            }

        if step == self.CONDITIONS:
            measure_start_date = None
            measure_type = None
            measure_details = self.get_cleaned_data_for_step(self.MEASURE_DETAILS)
            if measure_details:
                measure_start_date = measure_details.get("valid_between").lower
                measure_type = measure_details.get("measure_type")
            kwargs["form_kwargs"] = {
                "measure_start_date": measure_start_date,
                "measure_type": measure_type,
            }

        if step == self.SUMMARY:
            measure_details = self.get_cleaned_data_for_step(self.MEASURE_DETAILS)
            measure_type = (
                measure_details.get("measure_type") if measure_details else None
            )
            kwargs.update(
                {
                    "measure_type": measure_type,
                    "commodities_data": self.get_cleaned_data_for_step(
                        self.COMMODITIES,
                    ),
                    "conditions_data": self.get_cleaned_data_for_step(self.CONDITIONS),
                },
            )

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
            "measures/create-wizard-step.jinja",
        )


class MeasureUpdateBase(
    MeasureMixin,
    TrackedModelDetailMixin,
    CreateTaricUpdateView,
):
    form_class = forms.MeasureForm
    permission_required = "common.change_trackedmodel"
    queryset = Measure.objects.all()

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
        footnotes_formset = forms.MeasureUpdateFootnotesFormSet()
        footnotes_formset.initial = initial
        footnotes_formset.form_kwargs = {"path": self.request.path}
        context["footnotes_formset"] = footnotes_formset
        context["no_form_tags"] = FormHelper()
        context["no_form_tags"].form_tag = False
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
                prefix="measure-conditions-formset",
            )
        else:
            conditions_formset = forms.MeasureConditionsFormSet(
                initial=conditions_initial,
                prefix="measure-conditions-formset",
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

            initial_dict["applicable_duty"] = condition.condition_string
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
                component_output=MeasureConditionComponent,
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


class MeasureDelete(
    MeasureMixin,
    TrackedModelDetailMixin,
    CreateTaricDeleteView,
):
    form_class = forms.MeasureDeleteForm
    success_path = "list"


class MeasureMultipleDelete(MeasureSelectionQuerysetMixin, TemplateView, ListView):
    """UI for user review and deletion of multiple Measures."""

    template_name = "measures/delete-multiple-measures.jinja"

    def get_context_data(self, **kwargs):
        store_objects = self.get_queryset()
        self.object_list = store_objects
        context = super().get_context_data(**kwargs)

        return context

    def post(self, request):
        if request.POST.get("action", None) != "delete":
            # The user has cancelled out of the deletion process.
            return redirect("home")

        object_list = self.get_queryset()

        for obj in object_list:
            # make a new version of the object with an update type of delete.
            obj.new_version(
                workbasket=WorkBasket.current(request),
                update_type=UpdateType.DELETE,
            )
        self.session_store.clear()

        return redirect(reverse("workbaskets:review-workbasket"))


class MeasureSelectionUpdate(MeasureSessionStoreMixin, View):
    def post(self, request, *args, **kwargs):
        self.session_store.clear()
        data = json.loads(request.body)
        cleaned_data = {k: v for k, v in data.items() if "selectableobject_" in k}
        selected_objects = {k: v for k, v in cleaned_data.items() if v == 1}
        self.session_store.add_items(selected_objects)
        return JsonResponse(self.session_store.data)
