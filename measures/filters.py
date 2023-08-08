from datetime import date

from django import forms
from django.contrib.postgres.aggregates import StringAgg
from django.db.models import CharField
from django.db.models import Q
from django.urls import reverse_lazy
from django_filters import BooleanFilter
from django_filters import CharFilter
from django_filters import ChoiceFilter
from django_filters import DateFilter

from additional_codes.models import AdditionalCode
from certificates.models import Certificate
from commodities.helpers import get_measures_on_declarable_commodities
from commodities.models.orm import GoodsNomenclature
from common.filters import ActiveStateMixin
from common.filters import AutoCompleteFilter
from common.filters import TamatoFilter
from common.filters import TamatoFilterBackend
from common.forms import DateInputFieldFixed
from common.util import EndDate
from common.util import StartDate
from common.validators import NumericValidator
from footnotes.models import Footnote
from geo_areas.models import GeographicalArea
from measures.forms import MeasureFilterForm
from measures.models import Measure
from measures.models import MeasureType
from quotas.models import QuotaOrderNumber
from regulations.models import Regulation
from workbaskets.models import WorkBasket

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
        StringAgg("sid", delimiter=" ", output_field=CharField),
        StringAgg("description", delimiter=" ", output_field=CharField),
    )  # XXX order is significant


class MeasureFilter(TamatoFilter, ActiveStateMixin):
    def __init__(self, *args, **kwargs):
        if kwargs["data"]:
            kwargs["data"]._mutable = True
            if "start_date_modifier" not in kwargs["data"]:
                kwargs["data"]["start_date_modifier"] = "exact"
            if "end_date_modifier" not in kwargs["data"]:
                kwargs["data"]["end_date_modifier"] = "exact"
            kwargs["data"]._mutable = False
        super(MeasureFilter, self).__init__(*args, **kwargs)

    sid = CharFilter(
        label="ID",
        widget=forms.TextInput(),
        validators=[
            NumericValidator,
        ],
    )

    measure_type = AutoCompleteFilter(
        label="Type",
        field_name="measure_type__sid",
        queryset=MeasureType.objects.all(),
        attrs={
            "display_class": GOV_UK_TWO_THIRDS,
            "min_length": 3,
        },
    )

    goods_nomenclature = AutoCompleteFilter(
        label="Specific commodity code",
        field_name="goods_nomenclature__item_id",
        queryset=GoodsNomenclature.objects.all(),
        attrs={
            "display_class": GOV_UK_TWO_THIRDS,
            "min_length": 4,
        },
    )

    # Active measures only
    # See TODO #263
    is_active = BooleanFilter(
        label="WIP - Show active measures only",
        widget=forms.CheckboxInput,
        method="active_measure",
    )

    # measures in current workbasket
    # workbaskets - limbo state for when tarriff managers are making changes to tarriffs. Stored in session --> have a look at workbasket view summary. Have a look at get form quargs, may pass as var here.
    # current_workbasket = BooleanFilter(
    #     label="WIP - Only include measures in this current workbasket",
    #     widget=forms.CheckboxInput,
    #     field_name="",
    #     method="",
    # )

    # measures on declarable commodities
    # TODO: Invalidate if no code entered
    modc = BooleanFilter(
        label="Include inherited measures for specific commodity code",
        widget=forms.CheckboxInput,
        field_name="goods_nomenclature",
        method="commodity_modifier",
    )

    goods_nomenclature__item_id = CharFilter(
        label="Commodity code starting with",
        widget=forms.TextInput(
            attrs={
                "class": GOV_UK_TWO_THIRDS,
            },
        ),
        lookup_expr="startswith",
    )

    additional_code = AutoCompleteFilter(
        label="Additional code",
        field_name="additional_code",
        queryset=AdditionalCode.objects.all(),
        attrs={
            "display_class": GOV_UK_TWO_THIRDS,
            "min_length": 3,
        },
    )

    geographical_area = AutoCompleteFilter(
        label="Geographical area",
        field_name="geographical_area",
        queryset=GeographicalArea.objects.all(),
        attrs={
            "display_class": GOV_UK_TWO_THIRDS,
            "min_length": 2,
        },
    )

    order_number = AutoCompleteFilter(
        label="Quota order number",
        field_name="order_number__order_number",
        queryset=QuotaOrderNumber.objects.all(),
        attrs={
            "display_class": GOV_UK_TWO_THIRDS,
            "min_length": 4,
        },
    )

    regulation = AutoCompleteFilter(
        label="Regulation",
        field_name="generating_regulation__regulation_id",
        queryset=Regulation.objects.all(),
        attrs={
            "display_class": GOV_UK_TWO_THIRDS,
            "min_length": 3,
        },
    )

    footnote = AutoCompleteFilter(
        label="Footnote",
        field_name="footnotes",
        queryset=Footnote.objects.all(),
        attrs={
            "display_class": GOV_UK_TWO_THIRDS,
            "min_length": 2,
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

    certificates = AutoCompleteFilter(
        label="Certificates",
        field_name="certificates",
        queryset=Certificate.objects.all(),
        attrs={
            "display_class": GOV_UK_TWO_THIRDS,
        },
    )

    clear_url = reverse_lazy("measure-ui-search")

    def date_modifier(self, queryset, name, value):
        return queryset

    def commodity_modifier(self, queryset, name, value):
        if value:
            if self.data["goods_nomenclature"]:
                commodity = (
                    GoodsNomenclature.objects.filter(id=self.data["goods_nomenclature"])
                    .current()
                    .first()
                )

                queryset = get_measures_on_declarable_commodities(
                    WorkBasket.get_current_transaction(self.request),
                    commodity.item_id,
                )

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

    # TODO: copy/re-write the filter_active_state fn() from common/filters.py (don't need terminated)
    # using ActiveStateMixin doesn't filter by date, double check this works on bespoke version.

    def active_measure(self, queryset, name, value):
        current_date = date.today()

        if value is True:
            filter_query = Q(end_date__gt=current_date) | Q(end_date__isnull=True) & Q(
                start_date__lt=current_date,
            )
            queryset = (
                queryset.with_effective_valid_between()
                .annotate(start_date=StartDate("db_effective_valid_between"))
                .annotate(end_date=EndDate("db_effective_valid_between"))
                .filter(filter_query)
            )
            return queryset

        else:
            return queryset

    class Meta:
        model = Measure

        form = MeasureFilterForm

        # Defines the order shown in the form.
        fields = ["search", "sid", "active_state"]
