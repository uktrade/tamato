from datetime import date
from urllib.parse import urlencode

from django.contrib import messages
from django.urls import reverse
from django.utils.functional import cached_property
from django.views.generic import ListView
from rest_framework import permissions
from rest_framework import viewsets

from commodities import business_rules
from commodities import forms
from commodities.filters import CommodityFilter
from commodities.filters import GoodsNomenclatureFilterBackend
from commodities.helpers import get_measures_on_declarable_commodities
from commodities.models import GoodsNomenclature
from commodities.models.dc import CommodityCollectionLoader
from commodities.models.dc import CommodityTreeSnapshot
from commodities.models.dc import SnapshotMoment
from commodities.models.dc import get_chapter_collection
from commodities.models.orm import FootnoteAssociationGoodsNomenclature
from common.serializers import AutoCompleteSerializer
from common.views import SortingMixin
from common.views import TrackedModelDetailMixin
from common.views import TrackedModelDetailView
from common.views import WithPaginationListMixin
from common.views import WithPaginationListView
from measures.models import Measure
from workbaskets.models import WorkBasket
from workbaskets.views.generic import CreateTaricCreateView
from workbaskets.views.generic import CreateTaricDeleteView
from workbaskets.views.generic import CreateTaricUpdateView


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


class CommodityMixin:
    model = GoodsNomenclature

    def get_queryset(self):
        return GoodsNomenclature.objects.current()


class FootnoteAssociationMixin:
    model = FootnoteAssociationGoodsNomenclature

    def get_queryset(self):
        tx = WorkBasket.get_current_transaction(self.request)
        return FootnoteAssociationGoodsNomenclature.objects.approved_up_to_transaction(
            tx,
        )


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


class CommodityDetailFootnotes(CommodityMixin, TrackedModelDetailView):
    template_name = "includes/commodities/tabs/footnotes.jinja"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["commodity"] = self.object
        context["selected_tab"] = "footnotes"
        return context


class CommodityVersion(CommodityDetail):
    template_name = "includes/commodities/tabs/version_control.jinja"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["selected_tab"] = "version"
        return context


class CommodityMeasuresAsDefinedList(SortingMixin, WithPaginationListMixin, ListView):
    model = Measure
    paginate_by = 20
    template_name = "includes/commodities/tabs/measures-defined.jinja"
    sort_by_fields = ["measure_type", "start_date", "geo_area"]
    custom_sorting = {
        "start_date": "valid_between",
        "measure_type": "measure_type__sid",
        "geo_area": "geographical_area__area_id",
    }

    @property
    def commodity(self):
        return (
            GoodsNomenclature.objects.filter(sid=self.kwargs["sid"]).current().first()
        )

    def get_queryset(self):
        ordering = self.get_ordering()
        queryset = self.commodity.measures.current()
        if ordering:
            if isinstance(ordering, str):
                ordering = (ordering,)
            queryset = queryset.order_by(*ordering)
        return queryset

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["commodity"] = self.commodity
        context["selected_tab"] = "measures"

        url_params = urlencode({"goods_nomenclature": self.commodity.id})
        measures_url = f"{reverse('measure-ui-list')}?{url_params}"
        context["measures_url"] = measures_url
        return context


class CommodityHierarchy(CommodityDetail):
    template_name = "includes/commodities/tabs/hierarchy.jinja"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        context["selected_tab"] = "hierarchy"

        prefix = self.object.item_id[0:4]
        commodities_collection = CommodityCollectionLoader(prefix=prefix).load()

        tx = WorkBasket.get_current_transaction(self.request)
        snapshot = CommodityTreeSnapshot(
            commodities=commodities_collection.commodities,
            moment=SnapshotMoment(transaction=tx, date=date.today()),
        )

        context["snapshot"] = snapshot
        context["this_commodity"] = list(
            filter(lambda c: c.item_id == self.object.item_id, snapshot.commodities),
        )[0]

        return context


class MeasuresOnDeclarableCommoditiesList(CommodityMeasuresAsDefinedList):
    template_name = "includes/commodities/tabs/measures-declarable.jinja"
    sort_by_fields = ["measure_type", "start_date", "geo_area", "commodity"]
    custom_sorting = {
        "start_date": "valid_between",
        "measure_type": "measure_type__sid",
        "geo_area": "geographical_area__area_id",
        "commodity": "goods_nomenclature__item_id",
    }

    def get_queryset(self):
        ordering = self.get_ordering()
        tx = WorkBasket.get_current_transaction(self.request)
        queryset = get_measures_on_declarable_commodities(
            tx,
            self.commodity.item_id,
            date=date.today(),
        )

        if ordering:
            if isinstance(ordering, str):
                ordering = (ordering,)
            queryset = queryset.order_by(*ordering)

        return queryset

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["commodity"] = self.commodity

        context["selected_tab"] = "measures"

        url_params = urlencode({"goods_nomenclature": self.commodity.id, "modc": True})
        measures_url = f"{reverse('measure-ui-list')}?{url_params}"
        context["measures_url"] = measures_url

        return context


class CommodityAddFootnote(CreateTaricCreateView):
    form_class = forms.CommodityFootnoteForm
    template_name = "commodity_footnotes/create.jinja"

    validate_business_rules = (
        business_rules.NIG18,
        business_rules.NIG22,
        business_rules.NIG23,
        business_rules.NIG24,
    )
    model = FootnoteAssociationGoodsNomenclature

    @cached_property
    def commodity(self):
        return GoodsNomenclature.objects.current().get(sid=self.kwargs["sid"])

    @property
    def success_url(self):
        return reverse(
            "commodity-ui-add-footnote-confirm",
            kwargs={"pk": self.object.pk},
        )

    def get_initial(self):
        initial = super().get_initial()
        initial["goods_nomenclature"] = self.commodity
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tx"] = self.get_transaction()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["commodity"] = self.commodity
        return context


class CommodityAddFootnoteConfirm(FootnoteAssociationMixin, TrackedModelDetailView):
    template_name = "commodity_footnotes/confirm_create.jinja"
    required_url_kwargs = ("pk",)


class FootnoteAssociationGoodsNomenclatureUpdate(
    FootnoteAssociationMixin,
    TrackedModelDetailMixin,
    CreateTaricUpdateView,
):
    form_class = forms.CommodityFootnoteEditForm
    template_name = "commodity_footnotes/edit.jinja"
    success_path = "confirm-update"

    validate_business_rules = (
        business_rules.NIG18,
        business_rules.NIG22,
        business_rules.NIG23,
        business_rules.NIG24,
    )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tx"] = self.workbasket.new_transaction()
        return kwargs


class FootnoteAssociationGoodsNomenclatureConfirmUpdate(
    FootnoteAssociationMixin,
    TrackedModelDetailView,
):
    template_name = "commodity_footnotes/confirm_update.jinja"


class FootnoteAssociationGoodsNomenclatureDelete(
    FootnoteAssociationMixin,
    TrackedModelDetailMixin,
    CreateTaricDeleteView,
):
    template_name = "commodity_footnotes/delete.jinja"
    form_class = forms.FootnoteAssociationGoodsNomenclatureDeleteForm

    def get_success_url(self) -> str:
        return reverse(
            "footnote_association_goods_nomenclature-ui-confirm-delete",
            kwargs={"sid": self.object.goods_nomenclature.sid},
        )

    def form_valid(self, form):
        messages.success(
            self.request,
            f"Footnote association {self.object.associated_footnote.footnote_type.footnote_type_id}{self.object.associated_footnote.footnote_id} for commodity code {self.object.goods_nomenclature.item_id} has been deleted",
        )
        return super().form_valid(form)


class FootnoteAssociationGoodsNomenclatureConfirmDelete(
    CommodityMixin,
    TrackedModelDetailView,
):
    template_name = "commodity_footnotes/confirm_delete.jinja"
