import re
from collections import OrderedDict
from datetime import date
from functools import cached_property
from typing import Callable
from typing import Iterable
from typing import Optional
from typing import Union

from crispy_forms_gds.choices import Choice
from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Button
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import HTML
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from django import forms
from django.contrib.postgres.aggregates import StringAgg
from django.contrib.postgres.search import SearchVector
from django_filters import CharFilter
from django_filters import FilterSet
from django_filters import MultipleChoiceFilter
from rest_framework import filters
from rest_framework.settings import api_settings

ACTIVE_STATE_CHOICES = [Choice("active", "Active"), Choice("terminated", "Terminated")]


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


def last_10_years():
    current_year = date.today().year
    return [
        Choice(str(year), str(year))
        for year in range(current_year, current_year - 10, -1)
    ]


class LazyMultipleChoiceFilter(MultipleChoiceFilter):
    def get_field_choices(self):
        choices = self.extra.get("choices", [])
        if isinstance(choices, Callable):
            choices = choices()
        return choices

    @cached_property
    def field(self):
        field_kwargs = {**self.extra.copy(), "choices": self.get_field_choices()}
        field_kwargs.update(choices=self.get_field_choices())
        return self.field_class(label=self.label, **field_kwargs)


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

    search_fields: Iterable[Union[str, StringAgg]] = ("sid",)

    search_regex: Optional[re.Pattern] = None

    def get_search_term(self, value):
        value = value.strip()
        if self.search_regex:
            match = self.search_regex.search(value)
            if match:
                terms = list(match.groups())
                terms.extend(
                    [value[: match.start()].strip(), value[match.end() :].strip()]
                )
                return " ".join(terms)
        return value

    def search_queryset(self, queryset, search_term):
        search_term = self.get_search_term(search_term)
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
        search_term = request.query_params.get(api_settings.SEARCH_PARAM, "")
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


class ActiveStateMixin(FilterSet):
    """
    Generic filter mixin to provide an active state filter
    """

    active_state = MultipleChoiceFilter(
        choices=ACTIVE_STATE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        method="filter_active_state",
        label="Active state",
        help_text="Select all that apply",
        required=False,
    )

    def filter_active_state(self, queryset, name, value):
        active_status_filter = Q()
        current_date = TaricDateTimeRange(datetime.now(), datetime.now())
        if value == ["active"]:
            active_status_filter = Q(valid_between__upper_inf=True) | Q(
                valid_between__contains=current_date
            )
        if value == ["terminated"]:
            active_status_filter = Q(valid_between__fully_lt=current_date)

        return queryset.filter(active_status_filter)
