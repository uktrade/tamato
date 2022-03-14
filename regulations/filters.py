from django.urls import reverse_lazy

from common.filters import ActiveStateMixin
from common.filters import StartYearMixin
from common.filters import TamatoFilter
from common.filters import TamatoFilterBackend
from common.filters import TamatoFilterMixin
from regulations.models import Regulation


class RegulationFilterMixin(TamatoFilterMixin):
    """Filter mixin to allow custom filtering on regulation_id and
    information_text."""

    search_fields = ("regulation_id", "information_text")


class RegulationFilterBackend(TamatoFilterBackend, RegulationFilterMixin):
    pass


class RegulationFilter(
    TamatoFilter,
    RegulationFilterMixin,
    StartYearMixin,
    ActiveStateMixin,
):
    clear_url = reverse_lazy("regulation-ui-list")

    class Meta:
        model = Regulation
        fields = ["search", "start_year", "active_state"]
