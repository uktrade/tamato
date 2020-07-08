from django.contrib.postgres.search import SearchVector
from rest_framework import filters
from rest_framework.settings import api_settings


class TamatoFilterBackend(filters.BaseFilterBackend):
    search_fields = ("sid",)

    def get_search_term(self, request):
        return request.query_params.get(api_settings.SEARCH_PARAM, "")

    def filter_queryset(self, request, queryset, view):
        search_term = self.get_search_term(request)
        if search_term:
            return queryset.annotate(search=SearchVector(*self.search_fields)).filter(
                search=search_term
            )
        return filters.SearchFilter().filter_queryset(request, queryset, view)
