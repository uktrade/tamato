from django import forms
from django.contrib.postgres.aggregates import StringAgg
from django.db import models
from django.urls import reverse_lazy
from django_filters import BooleanFilter
from django_filters import CharFilter

from commodities.forms import CommodityFilterForm
from commodities.models.orm import GoodsNomenclature
from common.filters import ActiveStateMixin
from common.filters import TamatoFilter
from common.filters import TamatoFilterBackend
from common.validators import AlphanumericValidator
from common.validators import NumericValidator


class GoodsNomenclatureFilterBackend(TamatoFilterBackend):
    search_fields = (
        "item_id",
        StringAgg(
            "descriptions__description",
            delimiter=" ",
            output_field=models.CharField,
        ),
    )  # XXX order is significant

    def search_queryset(self, queryset, search_term):
        search_term = self.get_search_term(search_term)
        if search_term.isnumeric():
            return queryset.filter(item_id__startswith=search_term)

        return super().search_queryset(queryset, search_term)


class CommodityFilter(ActiveStateMixin, TamatoFilter):
    item_id = CharFilter(
        label="Code",
        widget=forms.TextInput(),
        lookup_expr="startswith",
        validators=[NumericValidator],
    )
    descriptions__description = CharFilter(
        label="Description",
        widget=forms.TextInput(),
        lookup_expr="icontains",
        validators=[AlphanumericValidator],
    )
    clear_url = reverse_lazy("commodity-ui-list")
    with_footnotes = BooleanFilter(
        label="Show commodity codes with footnotes",
        widget=forms.CheckboxInput(),
        field_name="associated_footnotes",
        method="footnotes_count",
    )

    def footnotes_count(self, queryset, name, value):
        if value:
            queryset = queryset.annotate(
                num_footnotes=models.Count("footnote_associations"),
            ).filter(num_footnotes__gt=0)

        return queryset

    class Meta:
        model = GoodsNomenclature
        form = CommodityFilterForm

        # Defines the order shown in the form.
        fields = ["search", "item_id", "active_state", "descriptions__description"]
