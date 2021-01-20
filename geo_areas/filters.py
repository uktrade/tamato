import logging

from django.contrib.postgres.aggregates import StringAgg
from django.urls import reverse_lazy
from django_filters import rest_framework as filters

from common.filters import TamatoFilter
from common.filters import TamatoFilterBackend
from common.filters import TamatoFilterMixin
from geo_areas.models import GeographicalArea
from geo_areas.validators import AreaCode

log = logging.getLogger(__name__)


class GeographicalAreaFilterMixin(TamatoFilterMixin):
    """
    Filter mixin to allow custom filtering on descriptions,
    SIDs and area_codes, area_id.
    """

    search_fields = (
        "sid",
        "area_code",
        "area_id",
        StringAgg("descriptions__description", delimiter=" "),
    )


class GeographicalAreaFilterBackend(TamatoFilterBackend, GeographicalAreaFilterMixin):
    pass


class GeographicalAreaFilter(TamatoFilter, GeographicalAreaFilterMixin):
    area_code = filters.TypedMultipleChoiceFilter(choices=AreaCode.choices, coerce=int)
    clear_url = reverse_lazy("geoarea-ui-list")

    class Meta:
        model = GeographicalArea
        fields = ["area_id", "sid", "area_code"]
