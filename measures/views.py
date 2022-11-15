from itertools import groupby
from operator import attrgetter
from typing import Any
from typing import Type

from crispy_forms.helper import FormHelper
from django.db.transaction import atomic
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView
from django.views.generic.list import ListView
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
from measures.models import MeasureConditionComponent
from measures.models import MeasureType
from measures.pagination import MeasurePaginator
from measures.parsers import DutySentenceParser
from measures.patterns import MeasureCreationPattern
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


class MeasureList(MeasureMixin, FormView, TamatoListView):
    """UI endpoint for viewing and filtering Measures."""

    template_name = "measures/list.jinja"
    filterset_class = MeasureFilter
    form_class = SelectableObjectsForm

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
            "DELETE_MEASURE_SELECTIONS",
        )
        # clear the store here before adding items
        # in case there was a previous form in progress that was abandoned
        store.clear()
        # If the user selects all, adds all the measures to the store
        select_all = self.request.POST.get("select-all-pages")
        if select_all:
            object_pks = {key: True for key, value in form.fields if value}
            store.add_items(object_pks)
        else:
            object_pks = {
                key: True for key, value in form.cleaned_data_no_prefix.items() if value
            }
            store.add_items(object_pks)

        url = reverse("measure-ui-delete-multiple")
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
class MeasureCreateWizard(
    NamedUrlSessionWizardView,
):
    storage_name = "measures.wizard.MeasureCreateSessionStorage"

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
        REGULATION_ID: {
            "title": "Enter the Regulation ID",
            "link_text": "Regulation ID",
        },
        QUOTA_ORDER_NUMBER: {
            "title": "Enter the Quota Order Number",
            "link_text": "Quota Order Number",
        },
        GEOGRAPHICAL_AREA: {
            "title": "Select the geographical area",
            "link_text": "Geographical areas",
            "info": "The measure will only apply to imports from or exports to the selected area. You can specify exclusions.",
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
        if step == self.COMMODITIES or step == self.CONDITIONS:
            # duty sentence validation requires the measure start date so pass it to form kwargs here
            valid_between = self.get_cleaned_data_for_step(self.MEASURE_DETAILS).get(
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
            "measures/create-wizard-step.jinja",
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
            parser = DutySentenceParser.get(
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
    CreateTaricDeleteView,
):
    form_class = forms.MeasureDeleteForm
    success_path = "list"


class MeasureMultipleDelete(TemplateView, ListView):
    """UI for user review and deletion of multiple Measures."""

    template_name = "measures/delete-multiple-measures.jinja"

    def _workbasket(self):
        """Get the current workbasket that is in session."""

        try:
            session_workbasket = self.request.session._session["workbasket"]
            workbasket = WorkBasket.objects.get(pk=session_workbasket["id"])
        except WorkBasket.DoesNotExist:
            workbasket = WorkBasket.objects.none()
        return workbasket

    def _session_store(self):
        """Get the session store to store the measures that will be deleted."""

        return SessionStore(
            self.request,
            "DELETE_MEASURE_SELECTIONS",
        )

    def get_queryset(self):
        """Get the measures that are candidates for deletion."""
        store = self._session_store()
        return Measure.objects.filter(pk__in=store.data.keys())

    def get_context_data(self, **kwargs):
        store_objects = self.get_queryset()
        self.object_list = store_objects
        context = super().get_context_data(**kwargs)

        return context

    def post(self, request):
        if request.POST.get("action", None) != "delete":
            # The user has cancelled out of the deletion process.
            return redirect("home")

        # By reverse ordering on record_code + subrecord_code we're able to
        # delete child entities first, avoiding protected foreign key
        # violations.
        object_list = self.get_queryset()
        # To do - figure out how to get record_ordering and reverse to work when added to this chain. Quotaset error.
        # .record_ordering().reverse()

        for obj in object_list:
            # make a new version of the object with an update type of delete.
            obj.new_version(
                workbasket=self._workbasket(),
                update_type=UpdateType.DELETE,
            )
        session_store = self._session_store()
        session_store.clear()

        return redirect(reverse("measure-ui-list"))
