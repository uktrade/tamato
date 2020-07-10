import re

from common.filters import TamatoFilterBackend
from footnotes.models import Footnote
from footnotes.validators import FOOTNOTE_ID_PATTERN
from footnotes.validators import FOOTNOTE_TYPE_ID_PATTERN


COMBINED_FOOTNOTE_AND_TYPE_ID = re.compile(
    r"^(?P<footnote_type_id>" + FOOTNOTE_TYPE_ID_PATTERN + ")"
    r"(?P<footnote_id>" + FOOTNOTE_ID_PATTERN + ")$"
)


class FootnoteFilterBackend(TamatoFilterBackend):
    """
    Filter that combines footnote type ID and footnote ID
    """

    search_fields = (
        "footnote_type__footnote_type_id",
        "footnote_id",
    )  # XXX order is important

    def get_search_term(self, request):
        search_term = super().get_search_term(request)
        match = COMBINED_FOOTNOTE_AND_TYPE_ID.match(search_term.strip())
        if match:
            return " ".join(match.groups())
        return search_term
