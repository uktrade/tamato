from django_filters import rest_framework as filters

from common.filters import TamatoFilter
from common.filters import TamatoFilterBackend
from common.filters import TamatoFilterMixin
from regulations.models import Regulation
from regulations.validators import RoleType


class RegulationFilterMixin(TamatoFilterMixin):
    """
    Filter mixin to allow custom filtering on regulation_id,
    role_type and information_text.
    """

    search_fields = ("regulation_id", "role_type", "information_text")


class RegulationFilterBackend(TamatoFilterBackend, RegulationFilterMixin):
    pass


class RegulationFilter(TamatoFilter, RegulationFilterMixin):
    role_type = filters.TypedMultipleChoiceFilter(choices=RoleType.choices, coerce=int)

    class Meta:
        model = Regulation
        fields = ["regulation_id", "role_type"]
