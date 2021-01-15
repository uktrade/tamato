import re
from datetime import date
from datetime import datetime
from datetime import timezone

from crispy_forms_gds.choices import Choice
from django import forms
from django.contrib.postgres.aggregates import StringAgg
from django.db.models import Q
from django_filters import CharFilter
from django_filters import MultipleChoiceFilter

from additional_codes.models import AdditionalCode
from additional_codes.validators import TypeChoices
from common.filters import TamatoFilter
from common.filters import TamatoFilterBackend
from common.filters import TamatoFilterMixin
from common.util import TaricDateTimeRange

COMBINED_ADDITIONAL_CODE_AND_TYPE_ID = re.compile(
    r"^(?P<type__sid>[A-Z0-9])(?P<code>[A-Z0-9]{3})$"
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


START_YEAR_CHOICES = tuple(  # Filter on the last 10 years
    Choice(str(year), str(year))
    for year in range(date.today().year, date.today().year - 10, -1)
)


class AdditionalCodeFilter(TamatoFilter, AdditionalCodeFilterMixin):
    """
    FilterSet for Additional Codes.

    Provides multiple choice widgets for Type SIDs, the start year
    of the additional code as well as filters for the code and SID
    """

    additional_code_type = MultipleChoiceFilter(
        choices=TypeChoices.choices,
        widget=forms.CheckboxSelectMultiple,
        field_name="type__sid",
        label="Additional Code Type",
        help_text="Select all that apply",
        required=False,
    )
    start_year = MultipleChoiceFilter(
        choices=START_YEAR_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        method="filter_start_year",
        label="Start Year",
        help_text="Select all that apply",
        required=False,
    )

    code = CharFilter(required=False)

    sid = CharFilter(required=False)

    def filter_start_year(self, queryset, name, value):
        """
        Provides a query for filtering on possible start years.

        DateTimeRanges sadly don't have a direct method for checking the start year
        (valid_between__lower__year= would have made sense but doesn't exist).
        Instead this creates a query to make sure the range contains Dec 31st of the
        given year, but not of the previous year.

        Edge-case: an Additional Code which starts in the given year, but ends in the same year
        before Dec 31st won't be included.
        """

        start_year_filter = Q()
        for year in value:
            contains_date = datetime(int(year), 12, 31, tzinfo=timezone.utc)
            fully_gt_date = datetime(int(year) - 1, 12, 31, tzinfo=timezone.utc)
            contains = TaricDateTimeRange(contains_date, contains_date)
            fully_gt = TaricDateTimeRange(fully_gt_date, fully_gt_date)
            start_year_filter = start_year_filter | Q(
                valid_between__contains=contains, valid_between__fully_gt=fully_gt
            )
        return queryset.filter(start_year_filter)

    class Meta:
        model = AdditionalCode

        # Defines the order shown in the form.
        fields = ["search", "additional_code_type", "start_year", "code", "sid"]
