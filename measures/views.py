import json
import logging
from itertools import groupby
from operator import attrgetter
from typing import Any
from typing import Dict
from typing import List
from typing import Type
from urllib.parse import urlencode

from crispy_forms.helper import FormHelper
from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db.models import Q
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.http import JsonResponse
from django.shortcuts import redirect
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.views import View
from django.views.generic.base import TemplateView
from django.views.generic.detail import DetailView
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import FormView
from django.views.generic.list import ListView
from django_filters.views import FilterView
from formtools.wizard.views import NamedUrlSessionWizardView
from rest_framework import viewsets
from rest_framework.reverse import reverse

from additional_codes.models import AdditionalCode
from certificates.models import Certificate
from commodities.models.orm import GoodsNomenclature
from common.forms import unprefix_formset_data
from common.models import TrackedModel
from common.pagination import build_pagination_list
from common.serializers import AutoCompleteSerializer
from common.util import TaricDateRange
from common.validators import UpdateType
from common.views import SortingMixin
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin
from common.views import TrackedModelDetailView
from common.views import WithPaginationListView
from footnotes.models import Footnote
from geo_areas import constants
from geo_areas.models import GeographicalArea
from geo_areas.models import GeographicalMembership
from geo_areas.utils import get_all_members_of_geo_groups
from geo_areas.validators import AreaCode
from measures import forms
from measures import models
from measures.conditions import show_step_geographical_area
from measures.conditions import show_step_quota_origins
from measures.constants import MEASURE_CONDITIONS_FORMSET_PREFIX
from measures.constants import START
from measures.constants import MeasureEditSteps
from measures.creators import MeasuresCreator
from measures.filters import MeasureCreateTaskFilter
from measures.filters import MeasureFilter
from measures.filters import MeasureTypeFilterBackend
from measures.models.bulk_processing import MeasuresBulkCreator
from measures.models.bulk_processing import ProcessingState
from measures.pagination import MeasurePaginator
from measures.parsers import DutySentenceParser
from measures.patterns import MeasureCreationPattern
from measures.util import diff_components
from regulations.models import Regulation
from workbaskets.forms import SelectableObjectsForm
from workbaskets.models import WorkBasket
from workbaskets.session_store import SessionStore
from workbaskets.validators import WorkflowStatus
from workbaskets.views.decorators import require_current_workbasket
from workbaskets.views.generic import CreateTaricDeleteView
from workbaskets.views.generic import CreateTaricUpdateView

logger = logging.getLogger(__name__)


class MeasureTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows measure types to be viewed."""

    serializer_class = AutoCompleteSerializer
    filter_backends = [MeasureTypeFilterBackend]

    def get_queryset(self):
        tx = WorkBasket.get_current_transaction(self.request)
        return models.MeasureType.objects.approved_up_to_transaction(tx).order_by(
            "description",
        )


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


class MeasureSearch(FilterView):
    """
    UI endpoint for filtering Measures.

    Does not list any measures. Redirects to MeasureList on form submit.
    """

    template_name = "measures/search.jinja"
    filterset_class = MeasureFilter

    def form_valid(self, form):
        return HttpResponseRedirect(reverse("measure-ui-list"))


class MeasureList(
    MeasureSelectionMixin,
    MeasureMixin,
    SortingMixin,
    FormView,
    TamatoListView,
):
    """UI endpoint for viewing and filtering Measures."""

    template_name = "measures/list.jinja"
    filterset_class = MeasureFilter
    form_class = SelectableObjectsForm
    sort_by_fields = ["sid", "measure_type", "geo_area", "start_date", "end_date"]
    custom_sorting = {
        "measure_type": "measure_type__sid",
        "geo_area": "geographical_area__area_id",
        "start_date": "valid_between",
        "end_date": "db_effective_end_date",
    }

    def dispatch(self, *args, **kwargs):
        if not self.request.GET:
            return HttpResponseRedirect(reverse("measure-ui-search"))
        return super().dispatch(*args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()

        ordering = self.get_ordering()

        if ordering:
            if ordering in "-db_effective_end_date":
                queryset = queryset.with_effective_valid_between()

            ordering = (ordering,)
            queryset = queryset.order_by(*ordering)

        return queryset

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        page = self.paginator.get_page(self.request.GET.get("page", 1))
        kwargs["objects"] = page.object_list
        return kwargs

    def cleaned_query_params(self):
        # Remove the sort_by and ordered params in order to stop them being duplicated in the base url
        if "sort_by" and "ordered" in self.filterset.data:
            cleaned_filterset = self.filterset.data.copy()
            cleaned_filterset.pop("sort_by")
            cleaned_filterset.pop("ordered")
            return cleaned_filterset
        else:
            return self.filterset.data

    def selected_filter_formatter(self) -> List[List[str]]:
        """
        A function that formats the selected filter choices into nicely written
        up strings.

        Those strings are then split into nested lists of 7 items to prepare
        them for template rendering.
        """
        selected_filters = {k: v for k, v in self.filterset.data.items() if v}
        selected_filters_strings = []

        if "goods_nomenclature" in selected_filters:
            goods = GoodsNomenclature.objects.current().get(
                id=selected_filters["goods_nomenclature"],
            )
            selected_filters_strings.append(
                f"Commodity Code {goods.autocomplete_label}",
            )

        if "goods_nomenclature__item_id" in selected_filters:
            selected_filters_strings.append(
                f"Commodity Code starting with {selected_filters['goods_nomenclature__item_id']}",
            )

        if "order_number" in selected_filters:
            selected_filters_strings.append(
                f"Quota Order Number {selected_filters['order_number']}",
            )

        if "sid" in selected_filters:
            selected_filters_strings.append(f"ID {selected_filters['sid']}")

        if "additional_code" in selected_filters:
            code = AdditionalCode.objects.current().get(
                id=selected_filters["additional_code"],
            )
            selected_filters_strings.append(f"Additional Code {code.structure_code}")

        if "certificates" in selected_filters:
            certificate = Certificate.objects.current().get(
                id=selected_filters["certificates"],
            )
            selected_filters_strings.append(f"Certificate {certificate.structure_code}")

        if "regulation" in selected_filters:
            regulation = Regulation.objects.current().get(
                id=selected_filters["regulation"],
            )
            selected_filters_strings.append(
                f"Regulation {regulation.autocomplete_label}",
            )

        if "measure_type" in selected_filters:
            measure_type = models.MeasureType.objects.current().get(
                id=selected_filters["measure_type"],
            )
            selected_filters_strings.append(
                f"Measure Type {measure_type.autocomplete_label}",
            )

        if "geographical_area" in selected_filters:
            area = GeographicalArea.objects.current().get(
                id=selected_filters["geographical_area"],
            )
            selected_filters_strings.append(f"{area.autocomplete_label}")

        if "footnote" in selected_filters:
            footnote = Footnote.objects.current().get(id=selected_filters["footnote"])
            selected_filters_strings.append(f"Footnote {footnote.structure_code}")

        if all(
            sf in selected_filters
            for sf in ("start_date_0", "start_date_1", "start_date_1")
        ):
            if selected_filters["start_date_modifier"] == "exact":
                modifier = ""
            else:
                modifier = selected_filters["start_date_modifier"]
            selected_filters_strings.append(
                f"Start date: {modifier} {selected_filters['start_date_0']}/{selected_filters['start_date_1']}/{selected_filters['start_date_2']}",
            )

        if all(
            sf in selected_filters for sf in ("end_date_0", "end_date_1", "end_date_2")
        ):
            if selected_filters["end_date_modifier"] == "exact":
                modifier = ""
            else:
                modifier = selected_filters["end_date_modifier"]
            selected_filters_strings.append(
                f"End date: {modifier} {selected_filters['end_date_0']}/{selected_filters['end_date_1']}/{selected_filters['end_date_2']}",
            )

        if "modc" in selected_filters:
            selected_filters_strings.append("Include inherited measures")

        if "measure_filters_modifier" in selected_filters:
            selected_filters_strings.append("Filter by current workbasket")

        # This splits the selected_filter_strings into nested lists of 7 so that the lists can be shown side by side in the template.
        selected_filters_lists = [
            selected_filters_strings[x : x + 7]
            for x in range(0, len(selected_filters_strings), 7)
        ]

        return selected_filters_lists

    @cached_property
    def paginator(self):
        filterset_class = self.get_filterset_class()
        self.filterset = self.get_filterset(filterset_class)
        return MeasurePaginator(
            self.filterset.qs.select_related(
                "additional_code",
                "generating_regulation",
                "geographical_area",
                "goods_nomenclature",
                "measure_type",
                "order_number",
            ),
            per_page=40,
        )

    def get_context_data(self, **kwargs):
        # References to page or pagination in the template were heavily increasing load time. By setting everything we need in the context,
        # we can reduce load time
        page = self.paginator.get_page(self.request.GET.get("page", 1))
        context = {}
        context.update(
            {
                "filter": kwargs["filter"],
                "form": self.get_form(),
                "view": self,
                "is_paginated": True,
                "results_count": self.paginator.count,
                "results_limit_breached": self.paginator.limit_breached,
                "page_count": self.paginator.num_pages,
                "has_other_pages": page.has_other_pages(),
                "has_previous_page": page.has_previous(),
                "has_next_page": page.has_next(),
                "page_number": page.number,
                "list_items_count": self.paginator.per_page,
                "page_links": build_pagination_list(
                    page.number,
                    page.paginator.num_pages,
                ),
                "selected_filter_lists": self.selected_filter_formatter(),
            },
        )
        if context["has_previous_page"]:
            context["prev_page_number"] = page.previous_page_number()
        if context["has_next_page"]:
            context["next_page_number"] = page.next_page_number()

        context["measure_selections"] = models.Measure.objects.filter(
            pk__in=self.measure_selections,
        ).values_list("sid", flat=True)

        context["query_params"] = True
        context["base_url"] = (
            f'{reverse("measure-ui-list")}?{urlencode(self.cleaned_query_params())}'
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
            url = reverse("measure-ui-list") + "?" + params
        else:
            url = reverse("measure-ui-list")

        return HttpResponseRedirect(url)


class MeasureDetail(MeasureMixin, TrackedModelDetailView):
    model = models.Measure
    template_name = "measures/detail.jinja"
    queryset = models.Measure.objects.latest_approved()

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
        (
            MeasureEditSteps.GEOGRAPHICAL_AREA_EXCLUSIONS,
            forms.MeasureGeographicalAreaExclusionsFormSet,
        ),
    ]

    templates = {
        START: "measures/edit-multiple-start.jinja",
        MeasureEditSteps.GEOGRAPHICAL_AREA_EXCLUSIONS: "measures/edit-multiple-formset.jinja",
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
        MeasureEditSteps.GEOGRAPHICAL_AREA_EXCLUSIONS: {
            "title": "Edit the geographical area exclusions",
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
        if step not in [
            START,
            MeasureEditSteps.QUOTA_ORDER_NUMBER,
            MeasureEditSteps.GEOGRAPHICAL_AREA_EXCLUSIONS,
        ]:
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

    def update_measure_components(
        self,
        measure: models.Measure,
        duties: str,
        workbasket: WorkBasket,
    ):
        """Updates the measure components associated to the measure."""
        diff_components(
            instance=measure,
            duty_sentence=duties if duties else measure.duty_sentence,
            start_date=measure.valid_between.lower,
            workbasket=workbasket,
            transaction=workbasket.current_transaction,
        )

    def update_measure_condition_components(
        self,
        measure: models.Measure,
        workbasket: WorkBasket,
    ):
        """Updates the measure condition components associated to the
        measure."""
        conditions = measure.conditions.current()
        for condition in conditions:
            condition.new_version(
                dependent_measure=measure,
                workbasket=workbasket,
            )

    def update_measure_excluded_geographical_areas(
        self,
        edited: bool,
        measure: models.Measure,
        exclusions: List[GeographicalArea],
        workbasket: WorkBasket,
    ):
        """Updates the excluded geographical areas associated to the measure."""
        existing_exclusions = measure.exclusions.current()

        # Update any exclusions to new measure version
        if not edited:
            for exclusion in existing_exclusions:
                exclusion.new_version(
                    modified_measure=measure,
                    workbasket=workbasket,
                )
            return

        new_excluded_areas = get_all_members_of_geo_groups(
            validity=measure.valid_between,
            geo_areas=exclusions,
        )

        for geo_area in new_excluded_areas:
            existing_exclusion = existing_exclusions.filter(
                excluded_geographical_area=geo_area,
            ).first()
            if existing_exclusion:
                existing_exclusion.new_version(
                    modified_measure=measure,
                    workbasket=workbasket,
                )
            else:
                models.MeasureExcludedGeographicalArea.objects.create(
                    modified_measure=measure,
                    excluded_geographical_area=geo_area,
                    update_type=UpdateType.CREATE,
                    transaction=workbasket.new_transaction(),
                )

        removed_excluded_areas = {
            e.excluded_geographical_area for e in existing_exclusions
        }.difference(set(exclusions))

        exclusions_to_remove = [
            existing_exclusions.get(excluded_geographical_area__id=geo_area.id)
            for geo_area in removed_excluded_areas
        ]

        for exclusion in exclusions_to_remove:
            exclusion.new_version(
                update_type=UpdateType.DELETE,
                modified_measure=measure,
                workbasket=workbasket,
            )

    def update_measure_footnote_associations(self, measure, workbasket):
        """Updates the footnotes associated to the measure."""
        footnote_associations = (
            models.FootnoteAssociationMeasure.objects.current().filter(
                footnoted_measure__sid=measure.sid,
            )
        )
        for fa in footnote_associations:
            fa.new_version(
                footnoted_measure=measure,
                workbasket=workbasket,
            )

    def done(self, form_list, **kwargs):
        if settings.MEASURES_ASYNC_EDIT:
            return self.async_done(form_list, **kwargs)
        else:
            return self.sync_done(form_list, **kwargs)
        
    def async_done(self, form_list, **kwargs):
        pass


    def sync_done(self, form_list, **kwargs):
        cleaned_data = self.get_all_cleaned_data()
        selected_measures = self.get_queryset()
        workbasket = WorkBasket.current(self.request)
        new_start_date = cleaned_data.get("start_date", None)
        new_end_date = cleaned_data.get("end_date", False)
        new_quota_order_number = cleaned_data.get("order_number", None)
        new_generating_regulation = cleaned_data.get("generating_regulation", None)
        new_duties = cleaned_data.get("duties", None)
        new_exclusions = [
            e["excluded_area"]
            for e in cleaned_data.get("formset-geographical_area_exclusions", [])
        ]
        for measure in selected_measures:
            new_measure = measure.new_version(
                workbasket=workbasket,
                update_type=UpdateType.UPDATE,
                valid_between=TaricDateRange(
                    lower=(
                        new_start_date
                        if new_start_date
                        else measure.valid_between.lower
                    ),
                    upper=(
                        new_end_date
                        if new_end_date is not False
                        else measure.valid_between.upper
                    ),
                ),
                order_number=(
                    new_quota_order_number
                    if new_quota_order_number
                    else measure.order_number
                ),
                generating_regulation=(
                    new_generating_regulation
                    if new_generating_regulation
                    else measure.generating_regulation
                ),
            )
            self.update_measure_components(
                measure=new_measure,
                duties=new_duties,
                workbasket=workbasket,
            )
            self.update_measure_condition_components(
                measure=new_measure,
                workbasket=workbasket,
            )
            self.update_measure_excluded_geographical_areas(
                edited="geographical_area_exclusions"
                in cleaned_data.get("fields_to_edit", []),
                measure=new_measure,
                exclusions=new_exclusions,
                workbasket=workbasket,
            )
            self.update_measure_footnote_associations(
                measure=new_measure,
                workbasket=workbasket,
            )
        self.session_store.clear()

        return redirect(
            reverse(
                "workbaskets:workbasket-ui-review-measures",
                kwargs={"pk": workbasket.pk},
            ),
        )


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
    QUOTA_ORIGINS = "quota_origins"
    GEOGRAPHICAL_AREA = "geographical_area"
    COMMODITIES = "commodities"
    ADDITIONAL_CODE = "additional_code"
    CONDITIONS = "conditions"
    FOOTNOTES = "footnotes"
    SUMMARY = "summary"
    COMPLETE = "complete"

    data_form_list = [
        (MEASURE_DETAILS, forms.MeasureDetailsForm),
        (REGULATION_ID, forms.MeasureRegulationIdForm),
        (QUOTA_ORDER_NUMBER, forms.MeasureQuotaOrderNumberForm),
        (QUOTA_ORIGINS, forms.MeasureQuotaOriginsForm),
        (GEOGRAPHICAL_AREA, forms.MeasureGeographicalAreaForm),
        (COMMODITIES, forms.MeasureCommodityAndDutiesFormSet),
        (ADDITIONAL_CODE, forms.MeasureAdditionalCodeForm),
        (CONDITIONS, forms.MeasureConditionsWizardStepFormSet),
        (FOOTNOTES, forms.MeasureFootnotesFormSet),
    ]
    """Forms in this wizard's steps that collect user data."""

    form_list = [
        (START, forms.MeasureCreateStartForm),
        *data_form_list,
        (SUMMARY, forms.MeasureReviewForm),
    ]
    """All Forms in this wizard's steps, including both those that collect user
    data and those that don't."""

    templates = {
        START: "measures/create-start.jinja",
        MEASURE_DETAILS: "measures/create-wizard-step.jinja",
        REGULATION_ID: "measures/create-wizard-step.jinja",
        QUOTA_ORDER_NUMBER: "measures/create-wizard-step.jinja",
        QUOTA_ORIGINS: "measures/create-quota-origins-step.jinja",
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
        QUOTA_ORIGINS: {
            "title": "Select the quota origins",
            "link_text": "Quota origins",
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

    condition_dict = {
        QUOTA_ORIGINS: show_step_quota_origins,
        GEOGRAPHICAL_AREA: show_step_geographical_area,
    }
    """Override of dictionary that maps steps to either callables that return a
    boolean or boolean values that indicate whether a wizard step should be
    shown."""

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

    def show_step(self, step) -> bool:
        """Convenience function to check whether a wizard step should be shown
        and therefore has data."""
        condition = self.condition_dict.get(step, True)
        if callable(condition):
            condition = condition(self)
        return condition

    @property
    def workbasket(self) -> WorkBasket:
        return WorkBasket.current(self.request)

    def done(self, form_list, **kwargs):
        if settings.MEASURES_ASYNC_CREATION:
            return self.async_done(form_list, **kwargs)
        else:
            return self.sync_done(form_list, **kwargs)

    def create_measures(self, cleaned_data):
        """Synchronously create measures within the context of the view / web
        worker using accumulated data, `cleaned_data`, from all the necessary
        wizard forms."""

        measures_creator = MeasuresCreator(self.workbasket, cleaned_data)
        return measures_creator.create_measures()

    def sync_done(self, form_list, **kwargs):
        """
        Handles this wizard's done step to create measures within the context of
        the web worker process.

        Because measures creation can be computationally expensive, this can
        take an excessive amount of time within the context of HTTP request
        processing.
        """

        logger.info("Creating measures synchronously.")

        cleaned_data = self.get_all_cleaned_data()
        created_measures = self.create_measures(cleaned_data)
        context = self.get_context_data(
            form=None,
            created_measures=created_measures,
            **kwargs,
        )

        return render(self.request, "measures/confirm-create-multiple.jinja", context)

    def async_done(self, form_list, **kwargs):
        """Handles this wizard's done step, handing off most of the processing
        (creating measures) to an asynchronous, background process managed by
        Celery."""

        logger.info("Creating measures asynchronously.")

        serializable_data = self.all_serializable_form_data()
        serializable_form_kwargs = self.all_serializable_form_kwargs()

        measures_bulk_creator = models.MeasuresBulkCreator.objects.create(
            form_data=serializable_data,
            form_kwargs=serializable_form_kwargs,
            workbasket=self.workbasket,
            user=self.request.user,
        )
        measures_bulk_creator.schedule_task()

        return redirect(
            "measure-ui-create-confirm",
            expected_measures_count=measures_bulk_creator.expected_measures_count,
        )

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

    @property
    def measure_start_date(self):
        cleaned_data = self.get_cleaned_data_for_step(self.MEASURE_DETAILS)
        measure_start_date = (
            cleaned_data.get("valid_between").lower if cleaned_data else None
        )
        return measure_start_date

    @property
    def measure_type(self):
        cleaned_data = self.get_cleaned_data_for_step(self.MEASURE_DETAILS)
        measure_type = cleaned_data.get("measure_type") if cleaned_data else None
        return measure_type

    @property
    def quota_order_number(self):
        cleaned_data = self.get_cleaned_data_for_step(self.QUOTA_ORDER_NUMBER)
        order_number = cleaned_data.get("order_number") if cleaned_data else None
        return order_number

    def get_react_script(self, form):

        all_geo_areas = (
            GeographicalArea.objects.current()
            .with_latest_description()
            .as_at_today_and_beyond()
            .order_by("description")
        )
        exclusions_options = all_geo_areas
        groups_options = all_geo_areas.filter(area_code=AreaCode.GROUP)
        country_regions_options = all_geo_areas.exclude(
            area_code=AreaCode.GROUP,
        )

        group_initial = form.data.get(f"{self.prefix}-geographical_area_group", "")

        react_initial = {
            "geoAreaType": form.data.get(f"{form.prefix}-geo_area", ""),
            "ergaOmnesExclusions": [
                country["erga_omnes_exclusion"].pk
                for country in form.initial.get(
                    constants.ERGA_OMNES_EXCLUSIONS_FORMSET_PREFIX,
                    [],
                )
                if country["erga_omnes_exclusion"]
            ],
            "geographicalAreaGroup": group_initial,
            "geoGroupExclusions": [
                country["geo_group_exclusion"].pk
                for country in form.initial.get(
                    constants.GROUP_EXCLUSIONS_FORMSET_PREFIX,
                    [],
                )
                if country["geo_group_exclusion"]
            ],
            "countryRegions": [
                country["geographical_area_country_or_region"].pk
                for country in form.initial.get(
                    constants.COUNTRY_REGION_FORMSET_PREFIX,
                    [],
                )
                if country["geographical_area_country_or_region"]
            ],
        }

        geo_group_pks = [group.pk for group in groups_options]
        memberships = GeographicalMembership.objects.filter(
            geo_group__pk__in=geo_group_pks,
        ).prefetch_related("geo_group", "member")

        groups_with_members = {}

        for group_pk in geo_group_pks:
            members = memberships.filter(geo_group__pk=group_pk)
            groups_with_members[group_pk] = [m.member.pk for m in members]

        script = render_to_string(
            "includes/measures/geo_area_script.jinja",
            {
                "request": self.request,
                "initial": react_initial,
                "groups_with_members": groups_with_members,
                "exclusions_options": exclusions_options,
                "groups_options": groups_options,
                "country_regions_options": country_regions_options,
                "errors": form.errors,
            },
        )
        return script

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        context["step_metadata"] = self.step_metadata
        if form:
            context["form"].is_bound = False
        context["no_form_tags"] = FormHelper()
        context["no_form_tags"].form_tag = False
        if isinstance(form, forms.MeasureGeographicalAreaForm):
            context["script"] = self.get_react_script(form)
        return context

    def get_form_kwargs(self, step):
        kwargs = {}

        if step == self.QUOTA_ORIGINS and self.quota_order_number:
            origins = (
                self.quota_order_number.quotaordernumberorigin_set.current().as_at_today_and_beyond()
            )
            kwargs["objects"] = origins

        elif step == self.COMMODITIES:
            min_commodity_count = 0
            measure_details = self.get_cleaned_data_for_step(self.MEASURE_DETAILS)
            if measure_details:
                min_commodity_count = measure_details.get("min_commodity_count")
            # Kwargs expected by formset
            kwargs.update(
                {
                    "min_commodity_count": min_commodity_count,
                    "measure_start_date": self.measure_start_date,
                },
            )
            # Kwargs expected by forms in formset
            kwargs["form_kwargs"] = {
                "measure_type": self.measure_type,
            }

        elif step == self.CONDITIONS:
            kwargs["form_kwargs"] = {
                "measure_start_date": self.measure_start_date,
                "measure_type": self.measure_type,
            }

        elif step == self.SUMMARY:
            kwargs.update(
                {
                    "measure_type": self.measure_type,
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
        return self.fixup_form(form, tx)

    @classmethod
    def fixup_form(cls, form, transaction):
        """Filter queryset form fields to approved transactions up to the
        workbasket's current transaction."""
        forms = [form]
        if hasattr(form, "forms"):
            forms = form.forms
        for f in forms:
            if hasattr(f, "fields"):
                for field in f.fields.values():
                    if hasattr(field, "queryset"):
                        field.queryset = field.queryset.approved_up_to_transaction(
                            transaction,
                        )

        form.is_valid()
        if hasattr(form, "cleaned_data"):
            form.initial = form.cleaned_data

        return form

    def get_template_names(self):
        return self.templates.get(
            self.steps.current,
            "measures/create-wizard-step.jinja",
        )


class MeasuresWizardCreateConfirm(TemplateView):
    template_name = "measures/confirm-create-multiple-async.jinja"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["expected_measures_count"] = self.kwargs.get("expected_measures_count")
        return context


class MeasuresCreateProcessQueue(
    PermissionRequiredMixin,
    WithPaginationListView,
):
    """UI endpoint for bulk creating Measures process queue."""

    permission_required = [
        "common.add_trackedmodel",
        "common.change_trackedmodel",
    ]
    template_name = "measures/create-process-queue.jinja"
    model = models.MeasuresBulkCreator
    queryset = models.MeasuresBulkCreator.objects.filter(
        workbasket__status=WorkflowStatus.EDITING,
    ).order_by("-created_at")
    filterset_class = MeasureCreateTaskFilter

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["selected_link"] = "all"
        context["selected_tab"] = "measure-process-queue"
        processing_state = self.request.GET.get("processing_state")

        if processing_state == "PROCESSING":
            context["selected_link"] = "processing"
        elif processing_state == ProcessingState.CANCELLED:
            context["selected_link"] = "terminated"
        elif processing_state == ProcessingState.FAILED_PROCESSING:
            context["selected_link"] = "failed"
        elif processing_state == ProcessingState.SUCCESSFULLY_PROCESSED:
            context["selected_link"] = "completed"
        # Provide template access to some UI / view utility functions.
        context["status_tag_generator"] = self.status_tag_generator
        context["can_terminate_task"] = self.can_terminate_task
        context["is_task_failed"] = self.is_task_failed
        context["is_task_terminated"] = self.is_task_terminated
        # Apply the TAP standard date format within the UI.
        context["datetime_format"] = settings.DATETIME_FORMAT
        if context["selected_link"] == "processing":
            context["object_list"] = self.get_processing_queryset()
        return context

    def get_processing_queryset(self):
        """Returns a combined queryset of tasks either AWAITING_PROCESSING or
        CURRENTLY_PROCESSING."""

        return self.queryset.filter(
            Q(processing_state=ProcessingState.AWAITING_PROCESSING)
            | Q(processing_state=ProcessingState.CURRENTLY_PROCESSING),
        )

    def is_task_failed(self, task: models.MeasuresBulkCreator) -> bool:
        """
        Return True if the task is in a failed state.

        Return False otherwise.
        """

        return task.processing_state == ProcessingState.FAILED_PROCESSING

    def is_task_terminated(self, task: MeasuresBulkCreator) -> bool:
        """
        Return True if the task is in a cancelled state. Cancelled tasks are
        surfaced as 'terminated' in the UI.

        Return False otherwise.
        """

        return task.processing_state == ProcessingState.CANCELLED

    def can_terminate_task(self, task: MeasuresBulkCreator) -> bool:
        """
        Return True if a task is in a queued state and the current user is
        permitted to terminate a task.

        Return False otherwise.
        """

        if (
            self.request.user.is_superuser
            and task.processing_state in ProcessingState.queued_states()
        ):
            return True

        return False

    def status_tag_generator(self, task: models.MeasuresBulkCreator) -> dict:
        """Returns a dict with text and a CSS class for a UI-friendly label for
        a bulk creation task."""

        if task.processing_state in [
            ProcessingState.CURRENTLY_PROCESSING,
            ProcessingState.AWAITING_PROCESSING,
        ]:
            return {
                "text": "Processing",
                "tag_class": "tamato-badge-light-blue",
            }
        elif task.processing_state == ProcessingState.SUCCESSFULLY_PROCESSED:
            return {
                "text": "Completed",
                "tag_class": "tamato-badge-light-green",
            }
        elif task.processing_state == ProcessingState.FAILED_PROCESSING:
            return {
                "text": "Failed",
                "tag_class": "tamato-badge-light-red",
            }
        elif task.processing_state == ProcessingState.CANCELLED:
            return {
                "text": "Terminated",
                "tag_class": "tamato-badge-light-yellow",
            }
        else:
            return {
                "text": "",
                "tag_class": "",
            }


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

        workbasket = WorkBasket.current(request)
        object_list = self.get_queryset()

        for obj in object_list:
            # make a new version of the object with an update type of delete.
            obj.new_version(
                workbasket=workbasket,
                update_type=UpdateType.DELETE,
            )
        self.session_store.clear()

        return redirect(
            reverse(
                "workbaskets:workbasket-ui-review-measures",
                kwargs={"pk": workbasket.pk},
            ),
        )


class MeasureSelectionUpdate(MeasureSessionStoreMixin, View):
    def post(self, request, *args, **kwargs):
        self.session_store.clear()
        data = json.loads(request.body)
        cleaned_data = {k: v for k, v in data.items() if "selectableobject_" in k}
        selected_objects = {k: v for k, v in cleaned_data.items() if v == 1}
        self.session_store.add_items(selected_objects)
        return JsonResponse(self.session_store.data)


class CancelBulkProcessorTask(
    UserPassesTestMixin,
    SingleObjectMixin,
    FormView,
):
    """Attempt cancelling a bulk processor task."""

    permission_required = "measures.edit_bulkprocessor"
    model = models.MeasuresBulkCreator
    template_name = "measures/cancel-bulk-processor-task.jinja"
    form_class = forms.CancelBulkProcessorTaskForm

    def test_func(self) -> bool:
        """Method override used by UserPassesTestMixin to ensure this view's
        cancel behaviour is only available to superusers."""

        return self.request.user.is_superuser

    def dispatch(self, request, *args, **kwargs) -> HttpResponse:
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse(
            "cancel-bulk-processor-task-done",
            kwargs={"pk": self.object.pk},
        )

    def get_context_data(self, **kwargs) -> Dict:
        context = super().get_context_data(**kwargs)

        context["object"] = self.object
        context["datetime_format"] = settings.DATETIME_FORMAT

        return context

    def form_valid(self, form):
        self.object.cancel_task()
        return redirect(self.get_success_url())


class CancelBulkProcessorTaskDone(
    UserPassesTestMixin,
    DetailView,
):
    """Confirm attempt to cancel a bulk processor task."""

    model = models.MeasuresBulkCreator
    template_name = "measures/cancel-bulk-processor-task-done.jinja"

    def test_func(self) -> bool:
        """Method override used by UserPassesTestMixin to ensure this view's
        cancel behaviour is only available to superusers."""

        return self.request.user.is_superuser


class DutySentenceReference(TemplateView):
    template_name = "duties/duty_sentence_guide.jinja"

    @property
    def tx(self):
        return WorkBasket.get_current_transaction(self.request)

    def measurements(self):
        return (
            models.Measurement.objects.approved_up_to_transaction(
                self.tx,
            )
            .select_related("measurement_unit", "measurement_unit_qualifier")
            .order_by("measurement_unit__code")
        )

    def measurement_units(self):
        return models.MeasurementUnit.objects.approved_up_to_transaction(
            self.tx,
        ).order_by("code")

    def measurement_unit_qualifiers(self):
        return models.MeasurementUnitQualifier.objects.approved_up_to_transaction(
            self.tx,
        ).order_by("code")

    def monetary_units(self):
        return models.MonetaryUnit.objects.approved_up_to_transaction(self.tx).order_by(
            "code",
        )

    def duty_expressions(self):
        return models.DutyExpression.objects.approved_up_to_transaction(
            self.tx,
        ).order_by("sid")

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            duty_expressions=self.duty_expressions(),
            measurements=self.measurements(),
            measurement_units=self.measurement_units(),
            measurement_unit_qualifiers=self.measurement_unit_qualifiers(),
            monetary_units=self.monetary_units(),
            **kwargs,
        )
