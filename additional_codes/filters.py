import re
from datetime import date
from datetime import datetime
from typing import Callable

from crispy_forms_gds.choices import Choice
from django import forms
from django.contrib.postgres.aggregates import StringAgg
from django.db.models import DateTimeField
from django.db.models import Q
from django.db.models.functions import Extract
from django.db.models.functions import Lower
from django.urls import reverse_lazy
from django_filters import MultipleChoiceFilter

from additional_codes.models import AdditionalCode
from additional_codes.validators import TypeChoices
from common.filters import TamatoFilter
from common.filters import TamatoFilterBackend
from common.filters import TamatoFilterMixin
from common.util import TaricDateTimeRange


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


class LazyMultipleChoiceFilter(MultipleChoiceFilter):
    def get_field_choices(self):
        choices = self.extra.get("choices", [])
        if isinstance(choices, Callable):
            choices = choices()
        return choices

    @property
    def field(self):
        if not hasattr(self, "_field"):
            field_kwargs = self.extra.copy()

            field_kwargs.update(choices=self.get_field_choices())

            self._field = self.field_class(label=self.label, **field_kwargs)
        return self._field


class AdditionalCodeFilterBackend(TamatoFilterBackend, AdditionalCodeFilterMixin):
    pass


ACTIVE_STATE_CHOICES = [Choice("active", "Active"), Choice("terminated", "Terminated")]


def last_10_years():
    current_year = date.today().year
    return [
        Choice(str(year), str(year))
        for year in range(current_year, current_year - 10, -1)
    ]


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
                    Lower("valid_between", output_field=DateTimeField()), "year"
                )
            ).filter(start_year__in=value)
        return queryset

    def filter_active_state(self, queryset, name, value):

        active_status_filter = Q()
        current_date = TaricDateTimeRange(datetime.now(), datetime.now())
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
        fields = ["search", "additional_code_type", "start_year"]
