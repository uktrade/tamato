from django_filters import rest_framework as filters

from regulations.models import Regulation


class RegulationFilter(filters.FilterSet):
    class Meta:
        model = regulation
        fields = ["regulation_id", "regulation_type__regulation_type_id"]
