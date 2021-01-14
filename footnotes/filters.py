import re

from django.contrib.postgres.aggregates import StringAgg

from common.filters import TamatoFilter
from common.filters import TamatoFilterBackend
from common.filters import TamatoFilterMixin
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


class FootnoteFilter(TamatoFilter, FootnoteFilterMixin):
    class Meta:
        model = models.Footnote
        fields = ["footnote_id", "footnote_type__footnote_type_id"]
