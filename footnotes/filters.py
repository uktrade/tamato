import re
from datetime import date

from crispy_forms_gds.choices import Choice
from django import forms
from django.contrib.postgres.aggregates import StringAgg
from django.db.models import DateTimeField
from django.db.models import Q
from django.db.models.functions import Extract
from django.db.models.functions import Lower
from django.urls import reverse_lazy
from django_filters import MultipleChoiceFilter

from common.filters import ACTIVE_STATE_CHOICES
from common.filters import last_10_years
from common.filters import LazyMultipleChoiceFilter
from common.filters import TamatoFilter
from common.filters import TamatoFilterBackend
from common.filters import TamatoFilterMixin
from common.util import TaricDateRange
from footnotes import models
from footnotes.validators import FOOTNOTE_ID_PATTERN
from footnotes.validators import FOOTNOTE_TYPE_ID_PATTERN


COMBINED_FOOTNOTE_AND_TYPE_ID = re.compile(
    r"^(?P<footnote_type_id>" + FOOTNOTE_TYPE_ID_PATTERN + ")"
    r"(?P<footnote_id>" + FOOTNOTE_ID_PATTERN + ")$"
)


class FootnoteFilterMixin(TamatoFilterMixin):
    """
    Filter mixin to allow custom filtering on descriptions,
    footnote type ID and footnote id.

    Also provides a regex to split combined footnote type IDs and footnote IDs.
    e.g. "CA001" -> "CA", "001"
    """

    search_fields = (
        StringAgg("footnote_type__footnote_type_id", delimiter=" "),
        "footnote_id",
        StringAgg("descriptions__description", delimiter=" "),
    )  # XXX order is important

    search_regex = COMBINED_FOOTNOTE_AND_TYPE_ID


class FootnoteFilterBackend(TamatoFilterBackend, FootnoteFilterMixin):
    pass


def footnote_type_choices():
    footnote_types = models.FootnoteType.objects.current()
    return [
        Choice(
            footnote_type.footnote_type_id,
            "{0} - {1}".format(
                footnote_type.footnote_type_id, footnote_type.description
            ),
        )
        for footnote_type in footnote_types
    ]


class FootnoteFilter(TamatoFilter, FootnoteFilterMixin):

    footnote_type = LazyMultipleChoiceFilter(
        choices=footnote_type_choices,
        widget=forms.CheckboxSelectMultiple,
        field_name="footnote_type__footnote_type_id",
        label="Footnote Type",
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
        current_date = TaricDateRange(date.today(), date.today())
        if value == ["active"]:
            active_status_filter = Q(valid_between__upper_inf=True) | Q(
                valid_between__contains=current_date
            )
        if value == ["terminated"]:
            active_status_filter = Q(valid_between__fully_lt=current_date)

        return queryset.filter(active_status_filter)

    clear_url = reverse_lazy("additional_code-ui-list")

    class Meta:
        model = models.Footnote
        fields = ["search"]
