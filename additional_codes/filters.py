import re
from datetime import date

from django import forms
from django.contrib.postgres.aggregates import StringAgg
from django.db.models import DateField
from django.db.models import Q
from django.db.models.functions import Extract
from django.db.models.functions import Lower
from django.urls import reverse_lazy
from django_filters import MultipleChoiceFilter

from additional_codes.models import AdditionalCode
from additional_codes.validators import TypeChoices
from common.filters import ACTIVE_STATE_CHOICES
from common.filters import last_10_years
from common.filters import LazyMultipleChoiceFilter
from common.filters import TamatoFilter
from common.filters import TamatoFilterBackend
from common.filters import TamatoFilterMixin
from common.util import TaricDateRange


COMBINED_ADDITIONAL_CODE_AND_TYPE_ID = re.compile(
    r"(?P<type__sid>[A-Z0-9])(?P<code>[A-Z0-9]{3})"
)


class AdditionalCodeFilterMixin(TamatoFilterMixin):
    """
    Filter mixin to allow custom filtering on type__sid, sid,
    code and description.

    Also provides a regex to split combined type__sid and code.
    e.g. "8001" -> "8", "001"
    """

    search_fields = (
        StringAgg("type__sid", delimiter=" "),
        "code",
        "sid",
        StringAgg("descriptions__description", delimiter=" "),
    )  # XXX order is significant

    search_regex = COMBINED_ADDITIONAL_CODE_AND_TYPE_ID


class AdditionalCodeFilterBackend(TamatoFilterBackend, AdditionalCodeFilterMixin):
    pass


class AdditionalCodeFilter(TamatoFilter, AdditionalCodeFilterMixin):
    """
    FilterSet for Additional Codes.

    Provides multiple choice widgets for Type SIDs, the start year
    of the additional code as well as filters for the code and SID
    """

    additional_code_type = LazyMultipleChoiceFilter(
        choices=TypeChoices.choices,
        widget=forms.CheckboxSelectMultiple,
        field_name="type__sid",
        label="Additional Code Type",
        help_text="Select all that apply",
        required=False,
    )

    start_year = LazyMultipleChoiceFilter(
        choices=last_10_years,
        widget=forms.CheckboxSelectMultiple,
        method="filter_start_year",
        label="Start Year",
        help_text="Select all that apply",
        required=False,
    )

    active_state = MultipleChoiceFilter(
        choices=ACTIVE_STATE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        method="filter_active_state",
        label="Active state",
        help_text="Select all that apply",
        required=False,
    )

    clear_url = reverse_lazy("additional_code-ui-list")

    def filter_start_year(self, queryset, name, value):
        if value:
            queryset = queryset.annotate(
                start_year=Extract(
                    Lower("valid_between", output_field=DateField()), "year"
                )
            ).filter(start_year__in=value)
        return queryset

    def filter_active_state(self, queryset, name, value):

        active_status_filter = Q()
        current_date = TaricDateRange(date.today(), date.today())
        if value == ["active"]:
            active_status_filter = Q(valid_between__upper_inf=True) | Q(
                valid_between__contains=current_date
            )
        if value == ["terminated"]:
            active_status_filter = Q(valid_between__fully_lt=current_date)

        return queryset.filter(active_status_filter)

    class Meta:
        model = AdditionalCode
        # Defines the order shown in the form.
        fields = ["search"]
