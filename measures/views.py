from typing import Any
from typing import Type

from crispy_forms.helper import FormHelper
from django.core.exceptions import ValidationError
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils.decorators import classonlymethod
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
from measures.models import Measure
from measures.models import MeasureCondition
from measures.models import MeasureConditionComponent
from measures.models import MeasureType
from measures.patterns import MeasureCreationPattern
from workbaskets.models import WorkBasket
from workbaskets.views.decorators import require_current_workbasket
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

    queryset = Measure.objects.with_duty_sentence().latest_approved()
    template_name = "measures/list.jinja"
    filterset_class = MeasureFilter


class MeasureDetail(MeasureMixin, TrackedModelDetailView):
    model = Measure
    template_name = "measures/detail.jinja"
    queryset = Measure.objects.with_duty_sentence().latest_approved()


@method_decorator(require_current_workbasket, name="dispatch")
class MeasureCreateWizard(
    NamedUrlSessionWizardView,
):
    storage_name = "measures.wizard.MeasureCreateSessionStorage"

    STEPS = [
        (
            "start",
            {
                "form_class": forms.MeasureCreateStartForm,
                "title": "Create a new measure",
                "link_text": "Start",
                "template": "measures/create-start.jinja",
            },
        ),
        (
            "measure_details",
            {
                "form_class": forms.MeasureDetailsForm,
                "title": "Enter the basic data",
                "link_text": "Measure details",
            },
        ),
        (
            "commodity",
            {
                "form_class": forms.MeasureCommodityForm,
                "title": "Select commodity and additional code",
                "link_text": "Commodity and additional code",
            },
        ),
        (
            "conditions",
            {
                "form_class": forms.MeasureConditionsFormSet,
                "title": "Add one or more conditions",
                "link_text": "Conditions",
                "template": "measures/create-formset.jinja",
            },
        ),
        (
            "duties",
            {
                "form_class": forms.MeasureDutiesForm,
                "title": "Enter the duties that will apply",
                "link_text": "Duties",
            },
        ),
        (
            "footnotes",
            {
                "form_class": forms.MeasureFootnotesFormSet,
                "title": "Add one or more footnotes",
                "link_text": "Footnotes",
                "template": "measures/create-formset.jinja",
            },
        ),
        (
            "summary",
            {
                "form_class": forms.MeasureReviewForm,
                "title": "Review your measure",
                "link_text": "Summary",
                "template": "measures/create-review.jinja",
            },
        ),
    ]

    def done(self, *args, **kwargs):
        cleaned_data = self.get_all_cleaned_data()

        measure_start_date = cleaned_data["valid_between"].lower

        measure_creation_pattern = MeasureCreationPattern(
            workbasket=WorkBasket.current(self.request),
            base_date=measure_start_date,
            defaults={
                "generating_regulation": cleaned_data["generating_regulation"],
            },
        )

        measure_data = {
            "measure_type": cleaned_data["measure_type"],
            "geographical_area": cleaned_data["geographical_area"],
            "exclusions": cleaned_data.get("geo_area_exclusions", []),
            "goods_nomenclature": cleaned_data["goods_nomenclature"],
            "additional_code": cleaned_data["additional_code"],
            "order_number": cleaned_data["order_number"],
            "validity_start": measure_start_date,
            "validity_end": cleaned_data["valid_between"].upper,
            "footnotes": [
                item["footnote"]
                for item in cleaned_data.get("formset-footnotes", [])
                if not item["DELETE"]
            ],
            # condition_sentence here, or handle separately and duty_sentence after?
            "duty_sentence": cleaned_data["duties"],
        }

        try:
            measure = measure_creation_pattern.create(**measure_data)
            for i, condition_data in enumerate(
                cleaned_data.get("formset-conditions", []),
            ):

                condition = MeasureCondition(
                    sid=measure_creation_pattern.measure_condition_sid_counter(),
                    component_sequence_number=i,
                    dependent_measure=measure,
                    update_type=UpdateType.CREATE,
                    transaction=measure.transaction,
                    condition_code=condition_data["condition_code"],
                    action=condition_data.get("action"),
                    required_certificate=condition_data.get("required_certificate"),
                )
                condition.save()

                # XXX the design doesn't show whether the condition duty_amount field
                # should handle duty_expression, monetary_unit or measurements, so this
                # code assumes some sensible(?) defaults
                if condition.duty_amount:
                    component = MeasureConditionComponent(
                        condition=condition,
                        update_type=UpdateType.CREATE,
                        transaction=condition.transaction,
                        duty_expression=measure_creation_pattern.condition_sentence_parser.duty_expressions[
                            1
                        ],
                        duty_amount=condition.duty_amount,
                        monetary_unit=measure_creation_pattern.condition_sentence_parser.monetary_units[
                            "GBP"
                        ],
                        component_measurement=None,
                    )
                    component.save()

        except AssertionError as e:
            raise ValidationError(e) from e

        return HttpResponseRedirect(
            reverse_lazy("measure-ui-confirm-create", kwargs={"sid": measure.sid}),
        )

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        context["step_metadata"] = dict(self.STEPS)
        context["form"].is_bound = False
        context["no_form_tags"] = FormHelper()
        context["no_form_tags"].form_tag = False
        return context

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
        return dict(self.STEPS)[self.steps.current].get(
            "template",
            "measures/create-wizard-step.jinja",
        )

    @classonlymethod
    def as_view(cls, **initkwargs):
        return super().as_view(
            [(name, metadata["form_class"]) for name, metadata in cls.STEPS],
            url_name="measure-ui-create",
            done_step_name="complete",
            **initkwargs,
        )


class MeasureConfirmCreate(MeasureMixin, TrackedModelDetailView):
    template_name = "common/confirm_create.jinja"


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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        initial = self.request.session.get(
            f"formset_initial_{self.kwargs.get('sid')}",
            [],
        )
        formset = forms.MeasureFootnotesFormSet()
        formset.initial = initial
        formset.form_kwargs = {"path": self.request.path}
        context["formset"] = formset
        context["no_form_tags"] = FormHelper()
        context["no_form_tags"].form_tag = False

        return context

    def form_valid(self, form):
        """
        Gets updated object with form.save(), checks if this object has been
        deleted during save.

        If deleted, gets newly created measure by latest sid.
        """
        self.object = form.save()
        if self.object.update_type == UpdateType.DELETE:
            self.object = Measure.objects.filter().order_by("sid").last()

        return HttpResponseRedirect(self.get_success_url())


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
