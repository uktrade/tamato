from django import forms
from django.contrib.postgres.aggregates import StringAgg
from django.urls import reverse_lazy
from django_filters import CharFilter

from commodities.forms import CommodityFilterForm
from commodities.models.orm import GoodsNomenclature
from common.filters import ActiveStateMixin
from common.filters import TamatoFilter
from common.filters import TamatoFilterBackend


class GoodsNomenclatureFilterBackend(TamatoFilterBackend):
    search_fields = (
        "item_id",
        StringAgg("descriptions__description", delimiter=" "),
    )  # XXX order is significant

    def search_queryset(self, queryset, search_term):
        search_term = self.get_search_term(search_term)
        if search_term.isnumeric():
            return queryset.filter(item_id__startswith=search_term)

        return super().search_queryset(queryset, search_term)


class CommodityFilter(TamatoFilter, ActiveStateMixin):
    item_id = CharFilter(
        label="Code",
        widget=forms.TextInput(),
        lookup_expr="startswith",
    )
    clear_url = reverse_lazy("commodity-ui-list")

    class Meta:
        model = GoodsNomenclature
        form = CommodityFilterForm

        # Defines the order shown in the form.
        fields = ["search", "item_id", "active_state"]
