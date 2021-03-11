from django import forms
from django.db.models import DateField
from django.db.models import Q
from django.db.models.functions import Lower
from django.db.models.functions import Upper
from django.urls import reverse_lazy
from django_filters import CharFilter
from django_filters import ChoiceFilter
from django_filters import DateFilter

from common.filters import TamatoFilter
from common.forms import DateInputFieldFixed
from footnotes.filters import COMBINED_FOOTNOTE_AND_TYPE_ID
from measures.forms import MeasureFilterForm
from measures.models import Measure

BEFORE_EXACT_AFTER_CHOICES = (
    ("exact", "is"),
    ("before", "before"),
    ("after", "after"),
)


class GovUKDateFilter(DateFilter):
    field_class = DateInputFieldFixed


class MeasureFilter(TamatoFilter):
    def __init__(self, *args, **kwargs):
        if kwargs["data"]:
            kwargs["data"]._mutable = True
            if "start_date_modifier" not in kwargs["data"]:
                kwargs["data"]["start_date_modifier"] = "exact"
            if "end_date_modifier" not in kwargs["data"]:
                kwargs["data"]["end_date_modifier"] = "exact"
            kwargs["data"]._mutable = False
        super(MeasureFilter, self).__init__(*args, **kwargs)

    sid = CharFilter(label="ID", widget=forms.TextInput())

    measure_type = CharFilter(label="Type", field_name="measure_type__sid")

    goods_nomenclature = CharFilter(
        label="Commodity code",
        field_name="goods_nomenclature__item_id",
    )

    additional_code = CharFilter(
        label="Additional code",
        field_name="additional_code__sid",
    )

    geographical_area = CharFilter(
        label="Geographical area",
        field_name="geographical_area__area_id",
    )

    order_number = CharFilter(
        label="Quota order number",
        field_name="order_number__sid",
    )

    regulation = CharFilter(
        label="Regulation",
        field_name="generating_regulation__regulation_id",
    )

    footnote = CharFilter(label="Footnote", method="filter_footnotes")

    start_date = GovUKDateFilter(
        label="",
        method="filter_start_date",
    )

    start_date_modifier = ChoiceFilter(
        label="Start date",
        widget=forms.RadioSelect,
        method="date_modifier",
        empty_label=None,
        choices=BEFORE_EXACT_AFTER_CHOICES,
    )

    end_date_modifier = ChoiceFilter(
        label="End date",
        widget=forms.RadioSelect,
        method="date_modifier",
        empty_label=None,
        choices=BEFORE_EXACT_AFTER_CHOICES,
    )

    end_date = GovUKDateFilter(
        label="",
        method="filter_end_date",
    )

    clear_url = reverse_lazy("measure-ui-list")

    def date_modifier(self, queryset, name, value):
        return queryset

    def filter_footnotes(self, queryset, name, value):
        if value:
            match = COMBINED_FOOTNOTE_AND_TYPE_ID.match(value)
            if match:
                return queryset.filter(
                    footnotes__footnote_id=match.group("footnote_id"),
                    footnotes__footnote_type__footnote_type_id=match.group(
                        "footnote_type_id",
                    ),
                )
            return queryset.none()
        return queryset

    def filter_start_date(self, queryset, name, value):
        if value:
            modifier = self.data["start_date_modifier"]
            if modifier == "after":
                filter_query = Q(start_date__gt=value)
            elif modifier == "before":
                filter_query = Q(start_date__lt=value)
            else:
                filter_query = Q(start_date=value)
            queryset = queryset.annotate(
                start_date=Lower("valid_between", output_field=DateField()),
            ).filter(filter_query)
        return queryset

    def filter_end_date(self, queryset, name, value):
        if value:
            modifier = self.data["end_date_modifier"]
            if modifier == "after":
                filter_query = Q(end_date__gt=value) | Q(end_date__isnull=True)
            elif modifier == "before":
                filter_query = Q(end_date__lt=value)
            else:
                filter_query = Q(end_date=value)
            queryset = (
                queryset.with_effective_valid_between()
                .annotate(
                    end_date=Upper(
                        "db_effective_valid_between",
                        output_field=DateField(),
                    ),
                )
                .filter(filter_query)
            )
        return queryset

    class Meta:
        model = Measure

        form = MeasureFilterForm

        # Defines the order shown in the form.
        fields = ["search", "sid"]
