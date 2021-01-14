import re
from collections import OrderedDict
from typing import Optional

from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Button
from crispy_forms_gds.layout import Layout
from django import forms
from django.contrib.postgres.search import SearchVector
from django_filters import CharFilter
from django_filters import FilterSet
from rest_framework import filters
from rest_framework.settings import api_settings


class TamatoFilterForm(forms.Form):
    """
    Generic Filtering form which adds submit and clear buttons.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            *self.fields,
            Button("submit", "Search and Filter"),
            Button.secondary("clear", "Clear"),
        )


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

    search = CharFilter(method="filter_search", label="Search")

    def filter_search(self, queryset, name, value):
        return self.search_queryset(queryset, value)

    def get_form_class(self):
        """
        Direct copy of the super function, which replaces the default form
        with the TamatoFilterForm.
        """
        fields = OrderedDict(
            [(name, filter_.field) for name, filter_ in self.filters.items()]
        )

        form = TamatoFilterForm if self._meta.form == forms.Form else self._meta.form

        return type(str("%sForm" % self.__class__.__name__), (form,), fields)
