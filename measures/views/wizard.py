import logging
from typing import Dict
from typing import List

from crispy_forms_gds.helper import FormHelper
from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import redirect
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from formtools.wizard.views import NamedUrlSessionWizardView

from common.util import TaricDateRange
from common.validators import UpdateType
from geo_areas import constants
from geo_areas.models import GeographicalArea
from geo_areas.models import GeographicalMembership
from geo_areas.utils import get_all_members_of_geo_groups
from geo_areas.validators import AreaCode
from measures import forms
from measures import models
from measures.conditions import show_step_geographical_area
from measures.conditions import show_step_quota_origins
from measures.constants import START
from measures.constants import MeasureEditSteps
from measures.creators import MeasuresCreator
from measures.util import diff_components
from measures.views.mixins import MeasureSerializableWizardMixin
from workbaskets.models import WorkBasket
from workbaskets.views.decorators import require_current_workbasket

from . import MeasureSelectionQuerysetMixin

logger = logging.getLogger(__name__)


@method_decorator(require_current_workbasket, name="dispatch")
class MeasureEditWizard(
    PermissionRequiredMixin,
    MeasureSelectionQuerysetMixin,
    NamedUrlSessionWizardView,
    MeasureSerializableWizardMixin,
):
    """
    Multipart form wizard for editing multiple measures.

    https://django-formtools.readthedocs.io/en/latest/wizard.html
    """

    storage_name = "measures.wizard.MeasureEditSessionStorage"
    permission_required = ["common.change_trackedmodel"]

    data_form_list = [
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
    """Forms in this wizard's steps that collect user data."""

    form_list = [
        (START, forms.MeasuresEditFieldsForm),
        *data_form_list,
    ]
    """All Forms in this wizard's steps, including both those that collect user
    data and those that don't."""

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
    
    @property
    def workbasket(self) -> WorkBasket:
        return WorkBasket.current(self.request)

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

    def done(self, form_list, **kwargs):
        if settings.MEASURES_ASYNC_EDIT:
            return self.async_done(form_list, **kwargs)
        else:
            return self.sync_done(form_list, **kwargs)

    def async_done(self, form_list, **kwargs):
        logger.info("Editing measures asynchronously.")
        serializable_data = self.all_serializable_form_data()
        serializable_form_kwargs = self.all_serializable_form_kwargs()

        db_selected_measures = []
        for measure in self.get_queryset():
            db_selected_measures.append(measure.id)

        measures_bulk_editor = models.MeasuresBulkEditor.objects.create(
            form_data=serializable_data,
            form_kwargs=serializable_form_kwargs,
            workbasket=self.workbasket,
            user=self.request.user,
            selected_measures=db_selected_measures,
        )
        self.session_store.clear()
        measures_bulk_editor.schedule_task()

        return redirect(
            reverse(
                "workbaskets:workbasket-ui-review-measures",
                kwargs={"pk": self.workbasket.pk},
            ),
        )

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
    MeasureSerializableWizardMixin

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
        erga_omnes = GeographicalArea.objects.erga_omnes().first()
        erga_omnes_exclusions_pks = [
            membership.member.pk
            for membership in GeographicalMembership.objects.filter(
                geo_group__pk=erga_omnes.pk,
            ).prefetch_related("member")
        ]
        erga_omnes_exclusions = all_geo_areas.filter(pk__in=erga_omnes_exclusions_pks)
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
                "erga_omnes_exclusions": erga_omnes_exclusions,
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
