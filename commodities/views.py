from datetime import date

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import FormView
from django.views.generic import ListView
from django.views.generic import TemplateView
from rest_framework import permissions
from rest_framework import viewsets

from commodities.filters import CommodityFilter
from commodities.filters import GoodsNomenclatureFilterBackend
from commodities.forms import CommodityImportForm
from commodities.models import GoodsNomenclature
from commodities.models.dc import CommodityCollectionLoader
from commodities.models.dc import CommodityTreeSnapshot
from commodities.models.dc import SnapshotMoment
from commodities.models.dc import get_chapter_collection
from common.serializers import AutoCompleteSerializer
from common.views import SortingMixin
from common.views import TrackedModelDetailView
from common.views import WithPaginationListMixin
from common.views import WithPaginationListView
from measures.models import Measure
from workbaskets.models import WorkBasket
from workbaskets.views.decorators import require_current_workbasket
from workbaskets.views.mixins import WithCurrentWorkBasket


class GoodsNomenclatureViewset(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows Goods Nomenclature to be viewed."""

    serializer_class = AutoCompleteSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [GoodsNomenclatureFilterBackend]

    def get_queryset(self):
        """
        API endpoint for autocomplete as used by the MeasureCreationWizard.

        Only return valid names that are products (suffix=80)
        """
        tx = WorkBasket.get_current_transaction(self.request)
        return (
            GoodsNomenclature.objects.approved_up_to_transaction(
                tx,
            )
            .prefetch_related("descriptions")
            .as_at_and_beyond(date.today())
            .filter(suffix=80)
        )


@method_decorator(require_current_workbasket, name="dispatch")
class CommodityImportView(PermissionRequiredMixin, FormView, WithCurrentWorkBasket):
    template_name = "commodities/import.jinja"
    form_class = CommodityImportForm
    success_url = reverse_lazy("commodity-ui-import-success")
    permission_required = [
        "common.add_trackedmodel",
        "common.change_trackedmodel",
    ]

    def form_valid(self, form):
        form.save(user=self.request.user, workbasket_id=self.workbasket.id)
        return super().form_valid(form)


class CommodityImportSuccessView(TemplateView):
    template_name = "commodities/import-success.jinja"


class CommodityMixin:
    model = GoodsNomenclature

    def get_queryset(self):
        return GoodsNomenclature.objects.current()


class CommodityList(CommodityMixin, WithPaginationListView):
    template_name = "commodities/list.jinja"
    filterset_class = CommodityFilter

    def get_queryset(self):
        return GoodsNomenclature.objects.current().order_by("item_id")

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["today"] = date.today()
        return context


class CommodityDetail(CommodityMixin, TrackedModelDetailView):
    template_name = "commodities/detail.jinja"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        indent = self.object.get_indent_as_at(date.today())
        context["indent_number"] = indent.indent if indent else "-"

        collection = get_chapter_collection(self.object)
        tx = WorkBasket.get_current_transaction(self.request)
        snapshot_date = self.object.valid_between.upper
        snapshot = collection.get_snapshot(tx, snapshot_date)
        commodity = snapshot.get_commodity(self.object, self.object.suffix)
        context["parent"] = snapshot.get_parent(commodity)
        context["commodity"] = self.object
        context["selected_tab"] = "details"

        return context


class CommodityVersion(CommodityDetail):
    template_name = "commodities/version_control.jinja"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["selected_tab"] = "version"
        return context


class CommodityMeasuresList(SortingMixin, WithPaginationListMixin, ListView):
    model = Measure
    paginate_by = 20
    template_name = "commodities/measures.jinja"
    sort_by_fields = ["measure_type", "start_date", "geo_area"]
    custom_sorting = {
        "start_date": "valid_between",
        "measure_type": "measure_type__sid",
        "geo_area": "geographical_area__area_id",
    }

    def get_queryset(self):
        ordering = self.get_ordering()
        commodity = (
            GoodsNomenclature.objects.filter(sid=self.kwargs["sid"]).current().first()
        )
        queryset = commodity.measures.as_at_today()
        if ordering:
            if isinstance(ordering, str):
                ordering = (ordering,)
            queryset = queryset.order_by(*ordering)
        return queryset

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["commodity"] = (
            GoodsNomenclature.objects.filter(sid=self.kwargs["sid"]).current().first()
        )
        context["selected_tab"] = "measures"
        return context


class Commodityhierarchy(CommodityDetail):
    template_name = "commodities/hierarchy.jinja"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        context["selected_tab"] = "hierarchy"

        prefix = self.object.item_id[0:4]
        commodities_collection = CommodityCollectionLoader(prefix=prefix).load()

        tx = WorkBasket.get_current_transaction(self.request)
        snapshot = CommodityTreeSnapshot(
            commodities=commodities_collection.commodities,
            moment=SnapshotMoment(transaction=tx),
        )

        context["snapshot"] = snapshot
        context["this_commodity"] = list(
            filter(lambda c: c.item_id == self.object.item_id, snapshot.commodities),
        )[0]

        return context
