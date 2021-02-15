import re

from django.contrib.postgres.aggregates import StringAgg
from django.forms import CheckboxSelectMultiple
from django.urls import reverse_lazy

from additional_codes.models import AdditionalCode
from additional_codes.validators import TypeChoices
from common.filters import ActiveStateMixin
from common.filters import LazyMultipleChoiceFilter
from common.filters import StartYearMixin
from common.filters import TamatoFilter
from common.filters import TamatoFilterBackend
from common.filters import TamatoFilterMixin

COMBINED_ADDITIONAL_CODE_AND_TYPE_ID = re.compile(
    r"(?P<type__sid>[A-Z0-9])(?P<code>[A-Z0-9]{3})",
)


class AdditionalCodeFilterMixin(TamatoFilterMixin):
    """
    Filter mixin to allow custom filtering on type__sid, sid, code and
    description.

    Also provides a regex to split combined type__sid and code. e.g. "8001" ->
    "8", "001"
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


class AdditionalCodeFilter(
    TamatoFilter,
    AdditionalCodeFilterMixin,
    StartYearMixin,
    ActiveStateMixin,
):
    """
    FilterSet for Additional Codes.

    Provides multiple choice widgets for Type SIDs, the start year of the
    additional code as well as filters for the code and SID
    """

    additional_code_type = LazyMultipleChoiceFilter(
        choices=TypeChoices.choices,
        widget=CheckboxSelectMultiple,
        field_name="type__sid",
        label="Additional Code Type",
        help_text="Select all that apply",
        required=False,
    )

    clear_url = reverse_lazy("additional_code-ui-list")

    class Meta:
        model = AdditionalCode
        # Defines the order shown in the form.
        fields = ["search", "additional_code_type", "start_year", "active_state"]
