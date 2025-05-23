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
from measures.models import MeasureCondition
from measures.models import MeasureType
from measures.models.bulk_processing import MeasuresBulkCreator
from measures.models.bulk_processing import MeasuresBulkEditor
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


class MeasureFilter(TamatoFilter):
    def __init__(self, *args, **kwargs):
        if kwargs["data"]:
            data = kwargs["data"].copy()
            if "start_date_modifier" not in data:
                data["start_date_modifier"] = "exact"
            if "end_date_modifier" not in data:
                data["end_date_modifier"] = "exact"
            kwargs["data"] = data
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

    # measures on declarable commodities
    modc = BooleanFilter(
        label="Include inherited measures",
        widget=forms.CheckboxInput(),
        field_name="goods_nomenclature",
        method="commodity_modifier",
    )

    workbasket = BooleanFilter(
        label="Filter by current workbasket",
        widget=forms.CheckboxInput(),
        method="workbasket_filter",
        required=False,
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
        field_name="conditions__required_certificate",
        queryset=Certificate.objects.current(),
        method="certificates_filter",
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

    def workbasket_filter(self, queryset, name, value):
        if value:
            wb = WorkBasket.current(self.request)
            queryset = queryset.filter(transaction__workbasket=wb)

        return queryset

    def certificates_filter(self, queryset, name, value):
        """Filters the queryset for the current versions of measures associated
        to the certificate via `MeasureCondition`."""
        if value:
            measure_conditions = (
                MeasureCondition.objects.current()
                .filter(
                    required_certificate__version_group=value.version_group,
                )
                .select_related("dependent_measure")
            )

            measure_ids = []
            for condition in measure_conditions:
                try:
                    # `dependent_measure` may not be the latest version of the measure.
                    measure_ids.append(
                        condition.dependent_measure.get_versions().current().get().pk,
                    )
                except Measure.DoesNotExist:
                    # `.current()` returned an empty queryset because the measure has since been deleted.
                    continue

            queryset = queryset.filter(id__in=measure_ids)

        return queryset

    class Meta:
        model = Measure

        form = MeasureFilterForm

        # Defines the order shown in the form.
        fields = ["search", "sid"]


class MeasureCreateTaskFilter(TamatoFilter):
    """FilterSet for Bulk Measure Creation tasks."""

    search_fields = "processing_state"
    clear_url = reverse_lazy("measure-create-process-queue")

    class Meta:
        model = MeasuresBulkCreator
        fields = ["processing_state"]


class MeasureEditTaskFilter(TamatoFilter):
    """FilterSet for Bulk Measure Edit tasks."""

    search_fields = "processing_state"
    clear_url = reverse_lazy("measure-edit-process-queue")

    class Meta:
        model = MeasuresBulkEditor
        fields = ["processing_state"]
