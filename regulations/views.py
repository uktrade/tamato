from typing import Type

from rest_framework import viewsets

from common.models import TrackedModel
from common.serializers import AutoCompleteSerializer
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin
from common.views import TrackedModelDetailView
from regulations import business_rules
from regulations.filters import RegulationFilter
from regulations.filters import RegulationFilterBackend
from regulations.forms import RegulationCreateForm
from regulations.forms import RegulationDeleteForm
from regulations.forms import RegulationEditForm
from regulations.models import Regulation
from workbaskets.models import WorkBasket
from workbaskets.views.generic import CreateTaricCreateView
from workbaskets.views.generic import CreateTaricDeleteView
from workbaskets.views.generic import CreateTaricUpdateView
from workbaskets.views.generic import EditTaricView


class RegulationViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows regulations to be viewed."""

    serializer_class = AutoCompleteSerializer
    filter_backends = [RegulationFilterBackend]

    def get_queryset(self):
        tx = WorkBasket.get_current_transaction(self.request)
        return Regulation.objects.approved_up_to_transaction(tx).select_related(
            "regulation_group",
        )


class RegulationList(TamatoListView):
    """UI endpoint that allows regulations to be viewed."""

    queryset = Regulation.objects.latest_approved().select_related("regulation_group")
    template_name = "regulations/list.jinja"
    filterset_class = RegulationFilter
    search_fields = ["regulation_id", "pk"]


class RegulationMixin:
    model: Type[TrackedModel] = Regulation

    def get_queryset(self):
        tx = WorkBasket.get_current_transaction(self.request)
        return Regulation.objects.approved_up_to_transaction(tx).select_related(
            "regulation_group",
        )


class RegulationDetail(RegulationMixin, TrackedModelDetailView):
    required_url_kwargs = ("regulation_id",)
    template_name = "regulations/detail.jinja"


class RegulationCreateAndUpdateMixin(RegulationMixin, TrackedModelDetailMixin):
    template_name = "regulations/edit.jinja"
    form_class = RegulationEditForm
    validate_business_rules = (
        business_rules.ROIMB1,
        business_rules.ROIMB4,
        business_rules.ROIMB8,
        business_rules.ROIMB44,
        business_rules.ROIMB47,
    )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_violates(self, form):
        """
        Overrides to provide transaction of the most recently- updated
        associated measure if one exists, else transaction of the updated
        regulation.

        Note that updates to associated measures take place after the regulation
        has been updated and wouldn't be contained in the transaction of the
        regulation, meaning business rule ROIMB8 couldn't take them into
        account.
        """
        measure = self.object.measure_set.select_related("transaction").last()
        transaction = measure.transaction if measure else self.object.transaction

        return super().form_violates(
            form,
            transaction=transaction,
        )


class RegulationCreate(
    RegulationCreateAndUpdateMixin,
    CreateTaricCreateView,
):
    """UI to create new regulation CREATE instances."""

    template_name = "regulations/create.jinja"
    form_class = RegulationCreateForm


class RegulationEditCreate(
    RegulationCreateAndUpdateMixin,
    EditTaricView,
):
    """UI to edit regulation CREATE instances."""


class RegulationConfirmCreate(TrackedModelDetailView):
    template_name = "common/confirm_create.jinja"
    model = Regulation

    def get_queryset(self):
        tx = WorkBasket.get_current_transaction(self.request)
        return Regulation.objects.approved_up_to_transaction(tx)


class RegulationUpdate(
    RegulationCreateAndUpdateMixin,
    CreateTaricUpdateView,
):
    """UI to create regulation UPDATE instances."""

    def get_result_object(self, form):
        if form.instance.regulation_id == form.cleaned_data["regulation_id"]:
            return super().get_result_object(form)

        form.changed_data.append("regulation_id")
        obj = super().get_result_object(form)

        for measure in form.instance.measure_set.current():
            measure.new_version(
                generating_regulation=obj,
                workbasket=obj.transaction.workbasket,
            )

        return obj


class RegulationEditUpdate(
    RegulationCreateAndUpdateMixin,
    EditTaricView,
):
    """UI to edit regulation UPDATE instances."""


class RegulationConfirmUpdate(
    RegulationMixin,
    TrackedModelDetailView,
):
    template_name = "common/confirm_update.jinja"


class RegulationDelete(
    RegulationMixin,
    TrackedModelDetailMixin,
    CreateTaricDeleteView,
):
    form_class = RegulationDeleteForm
    success_path = "list"

    validate_business_rules = (business_rules.ROIMB46,)
