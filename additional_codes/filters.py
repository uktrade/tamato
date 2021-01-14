import re

from django.contrib.postgres.aggregates import StringAgg

from additional_codes.models import AdditionalCode
from common.filters import TamatoFilter
from common.filters import TamatoFilterBackend
from common.filters import TamatoFilterMixin

COMBINED_ADDITIONAL_CODE_AND_TYPE_ID = re.compile(
    r"^(?P<additional_code_type_id>[A-Z0-9])(?P<additional_code_id>[A-Z0-9]{3})$"
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
    class Meta:
        model = AdditionalCode
        fields = ["sid", "code", "type__sid"]
