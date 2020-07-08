import re

from common.filters import TamatoFilterBackend


COMBINED_ADDITIONAL_CODE_AND_TYPE_ID = re.compile(
    r"^(?P<additional_code_type_id>[A-Z0-9])(?P<additional_code_id>[A-Z0-9]{3})$"
)


class AdditionalCodeFilterBackend(TamatoFilterBackend):
    """
    Filter that combines additional code type ID and additional code ID
    """

    search_fields = "type__sid", "code"  # XXX order is significant

    def get_search_term(self, request):
        search_term = super().get_search_term(request)
        match = COMBINED_ADDITIONAL_CODE_AND_TYPE_ID.match(search_term.strip())
        if match:
            return " ".join(match.groups())
        return search_term
