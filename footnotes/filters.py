import logging
import re

from django_filters import rest_framework as filters

from footnotes.models import Footnote


log = logging.getLogger(__name__)

COMBINED_FOOTNOTE_AND_TYPE_ID = re.compile(
    r"(?P<footnote_type_id>[A-Z0-9]{2})(?P<footnote_id>[A-Z0-9]{3})"
)


class FootnoteFilter(filters.FilterSet):
    """
    Filter that combines footnote type ID and footnote ID
    """

    class Meta:
        model = Footnote
        fields = ["footnote_id", "footnote_type__footnote_type_id"]

    @property
    def qs(self):
        queryset = super().qs
        search_term = self.request.query_params.get("search", "")
        log.debug(f"Search term: {search_term}")
        match = COMBINED_FOOTNOTE_AND_TYPE_ID.match(search_term)
        if match:
            footnote_type_id, footnote_id = match.group(1, 2)
            log.debug(f"Match: {footnote_type_id}{footnote_id}")
            queryset = queryset.filter(
                footnote_id=footnote_id,
                footnote_type__footnote_type_id=footnote_type_id,
            )
        return queryset
