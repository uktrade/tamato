import re
from typing import Optional

from django.contrib.postgres.search import SearchVector
from django_filters import CharFilter
from django_filters import FilterSet
from rest_framework import filters
from rest_framework.settings import api_settings


class TamatoFilterMixin:
    """
    Generic filter mixin to provide basic search fields and an overrideable
    method for getting the search term.
    """

    search_fields = ("sid",)

    search_regex: Optional[re.Pattern] = None

    def get_search_term(self, value):
        if self.search_regex:
            match = self.search_regex.match(value.strip())
            if match:
                return " ".join(match.groups())
        return value

    def search_queryset(self, queryset, search_term):
        return queryset.annotate(search=SearchVector(*self.search_fields)).filter(
            search=search_term
        )


class TamatoFilterBackend(filters.BaseFilterBackend, TamatoFilterMixin):
    """
    Basic Filter for API views.

    This will grab the text from the `?search=` query param and do a full text search
    over the given `search_fields` - defaulting to SID only.
    """

    def filter_queryset(self, request, queryset, view):
        search_term = self.get_search_term(
            request.query_params.get(api_settings.SEARCH_PARAM, "")
        )
        if search_term:
            return self.search_queryset(queryset, search_term)
        return filters.SearchFilter().filter_queryset(request, queryset, view)


class TamatoFilter(FilterSet, TamatoFilterMixin):
    """
    Basic Filter for UI views.

    This will grab the text from the `?search=` query param and do a full text search
    over the given `search_fields` - defaulting to SID only.
    """

    search = CharFilter(method="filter_search")

    def filter_search(self, queryset, name, value):
        return self.search_queryset(queryset, value)
