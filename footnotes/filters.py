import re

from crispy_forms_gds.choices import Choice
from django.contrib.postgres.aggregates import StringAgg
from django.forms import CheckboxSelectMultiple
from django.urls import reverse_lazy

from common.filters import ActiveStateMixin
from common.filters import LazyMultipleChoiceFilter
from common.filters import StartYearMixin
from common.filters import TamatoFilter
from common.filters import TamatoFilterBackend
from common.filters import TamatoFilterMixin
from footnotes import models
from footnotes.validators import FOOTNOTE_ID_PATTERN
from footnotes.validators import FOOTNOTE_TYPE_ID_PATTERN

COMBINED_FOOTNOTE_AND_TYPE_ID = re.compile(
    r"^(?P<footnote_type_id>" + FOOTNOTE_TYPE_ID_PATTERN + ")"
    r"(?P<footnote_id>" + FOOTNOTE_ID_PATTERN + ")$",
)


class FootnoteFilterMixin(TamatoFilterMixin):
    """
    Filter mixin to allow custom filtering on descriptions, footnote type ID and
    footnote id.

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
                footnote_type.footnote_type_id,
                footnote_type.description,
            ),
        )
        for footnote_type in footnote_types
    ]


class FootnoteFilter(
    TamatoFilter,
    FootnoteFilterMixin,
    StartYearMixin,
    ActiveStateMixin,
):

    footnote_type = LazyMultipleChoiceFilter(
        choices=footnote_type_choices,
        widget=CheckboxSelectMultiple,
        field_name="footnote_type__footnote_type_id",
        label="Footnote Type",
        help_text="Select all that apply",
        required=False,
    )

    clear_url = reverse_lazy("additional_code-ui-list")

    class Meta:
        model = models.Footnote
        fields = ["search", "footnote_type", "start_year", "active_state"]
