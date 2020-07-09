import logging

from django.contrib.postgres.search import SearchVector
from django_filters import rest_framework as filters

from geo_areas.models import GeographicalArea
from geo_areas.validators import AreaCode

log = logging.getLogger(__name__)


class GeographicalAreaFilter(filters.FilterSet):
    area_code = filters.TypedMultipleChoiceFilter(choices=AreaCode.choices, coerce=int)

    class Meta:
        model = GeographicalArea
        fields = ["area_id", "sid", "area_code"]

    @property
    def qs(self):
        queryset = super().qs
        search_term = self.request.query_params.get("search", "")
        log.debug(f"Search term: {search_term}")
        if search_term:
            vector = SearchVector("id", "geographicalareadescription__description")
            queryset = queryset.annotate(search=vector).filter(search=search_term)
        return queryset
