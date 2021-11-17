from django import forms
from django.contrib.postgres.aggregates import StringAgg
from django.db.models import Q
from django.urls import reverse_lazy
from django_filters import CharFilter
from django_filters import ChoiceFilter
from django_filters import DateFilter

from additional_codes.models import AdditionalCode
from commodities.models.orm import GoodsNomenclature
from common.filters import AutoCompleteFilter
from common.filters import TamatoFilter
from common.filters import TamatoFilterBackend
from common.forms import DateInputFieldFixed
from common.util import EndDate
from common.util import StartDate
from footnotes.models import Footnote
from geo_areas.models import GeographicalArea
from measures.forms import MeasureFilterForm
from measures.models import Measure
from measures.models import MeasureType
from quotas.models import QuotaOrderNumber
from regulations.models import Regulation

BEFORE_EXACT_AFTER_CHOICES = (
    ("exact", "is"),
    ("before", "before"),
    ("after", "after"),
)

GOV_UK_TWO_THIRDS = "govuk-!-width-two-thirds"


class GovUKDateFilter(DateFilter):
    field_class = DateInputFieldFixed


class MeasureTypeFilterBackend(TamatoFilterBackend):
    search_fields = (
        StringAgg("sid", delimiter=" "),
        StringAgg("description", delimiter=" "),
    )  # XXX order is significant


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

    measure_type = AutoCompleteFilter(
        label="Type",
        field_name="measure_type__sid",
        queryset=MeasureType.objects.all(),
        attrs={
            "display_class": GOV_UK_TWO_THIRDS,
        },
    )

    goods_nomenclature = AutoCompleteFilter(
        label="Commodity code",
        field_name="goods_nomenclature__item_id",
        queryset=GoodsNomenclature.objects.all(),
        attrs={
            "display_class": GOV_UK_TWO_THIRDS,
        },
    )

    additional_code = AutoCompleteFilter(
        label="Additional code",
        field_name="additional_code",
        queryset=AdditionalCode.objects.all(),
        attrs={
            "display_class": GOV_UK_TWO_THIRDS,
        },
    )

    geographical_area = AutoCompleteFilter(
        label="Geographical area",
        field_name="geographical_area",
        queryset=GeographicalArea.objects.all(),
        attrs={
            "display_class": GOV_UK_TWO_THIRDS,
        },
    )

    order_number = AutoCompleteFilter(
        label="Quota order number",
        field_name="order_number__order_number",
        queryset=QuotaOrderNumber.objects.all(),
        attrs={
            "display_class": GOV_UK_TWO_THIRDS,
        },
    )

    regulation = AutoCompleteFilter(
        label="Regulation",
        field_name="generating_regulation__regulation_id",
        queryset=Regulation.objects.all(),
        attrs={
            "display_class": GOV_UK_TWO_THIRDS,
        },
    )

    footnote = AutoCompleteFilter(
        label="Footnote",
        field_name="footnotes",
        queryset=Footnote.objects.all(),
        attrs={
            "display_class": GOV_UK_TWO_THIRDS,
        },
    )

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
                start_date=StartDate("valid_between"),
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
                .annotate(end_date=EndDate("db_effective_valid_between"))
                .filter(filter_query)
            )
        return queryset

    class Meta:
        model = Measure

        form = MeasureFilterForm

        # Defines the order shown in the form.
        fields = ["search", "sid"]
