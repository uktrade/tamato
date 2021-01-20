import re
from collections import OrderedDict
from typing import Optional

from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Button
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import HTML
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from django import forms
from django.contrib.postgres.search import SearchVector
from django.urls import reverse
from django_filters import CharFilter
from django_filters import FilterSet
from rest_framework import filters
from rest_framework.settings import api_settings


def field_to_layout(field_name, field):
    """
    Converts fields into their GDS styled counterparts.

    If the counterpart is unknown, return the field_name as default
    """
    if isinstance(field, forms.CharField):
        return Field.text(field_name, label_size=Size.SMALL)
    if isinstance(field, forms.ChoiceField):
        return Field.checkboxes(field_name, legend_size=Size.SMALL)

    return field_name


class TamatoFilterForm(forms.Form):
    """
    Generic Filtering form which adds submit and clear buttons, and adds
    GDS formatting to field types.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()

        field_layout = (
            field_to_layout(field_name, field)
            for field_name, field in self.fields.items()
        )

        self.helper.layout = Layout(
            *field_layout,
            Button("submit", "Search and Filter"),
            HTML(
                f'<a class="govuk-button govuk-button--secondary" href="{self.clear_url}"> Clear </a>'
            ),
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
    clear_url = None

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

        if not self.clear_url:
            raise NotImplementedError(
                f"clear_url must be defined on {self.__class__.__name__}"
            )
        fields["clear_url"] = self.clear_url

        form = TamatoFilterForm if self._meta.form == forms.Form else self._meta.form

        return type(str("%sForm" % self.__class__.__name__), (form,), fields)
