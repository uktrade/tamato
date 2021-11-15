import re
from collections import OrderedDict
from datetime import date
from functools import cached_property
from typing import Callable
from typing import Iterable
from typing import Optional
from typing import Sequence
from typing import Union

from crispy_forms_gds.choices import Choice
from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import HTML
from crispy_forms_gds.layout import Button
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from django import forms
from django.contrib.postgres.aggregates import StringAgg
from django.contrib.postgres.search import SearchVector
from django.db.models import Q
from django.db.models.functions import Extract
from django.utils.safestring import mark_safe
from django_filters import CharFilter
from django_filters import FilterSet
from django_filters import MultipleChoiceFilter
from django_filters.constants import EMPTY_VALUES
from rest_framework import filters
from rest_framework.settings import api_settings

from common.fields import AutoCompleteField
from common.jinja2 import break_words
from common.models.tracked_qs import TrackedModelQuerySet
from common.util import StartDate
from common.util import TaricDateRange

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


def type_choices(queryset: TrackedModelQuerySet) -> Callable[[], Sequence[Choice]]:
    """
    Converts a model representing a type into a set of choices.

    The type model must have only one identifying field and have a description
    field.
    """
    if len(queryset.model.identifying_fields) != 1:
        raise TypeError("Model is required to have 1 identifying field only")
    field = queryset.model.identifying_fields[0]

    def get_choices():
        return [
            Choice(
                model.get_identifying_fields()[field],
                mark_safe(
                    "{0} - {1}".format(
                        model.get_identifying_fields()[field],
                        break_words(model.description),
                    ),
                ),
            )
            for model in queryset
        ]

    return get_choices


class MultiValueCharFilter(CharFilter):
    """
    Multiple words are passed in as a single string, which does not allow for
    lookup based on each word.

    This override splits the string on spaces into an array based and does a
    lookup on each word individually.
    """

    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs
        if self.distinct:
            qs = qs.distinct()
        lookup = f"{self.field_name}__in"
        return self.get_method(qs)(**{lookup: value.split()})


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
    """Generic Filtering form which adds submit and clear buttons, and adds GDS
    formatting to field types."""

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
                f'<a class="govuk-button govuk-button--secondary" href="{self.clear_url}"> Clear </a>',
            ),
        )


class TamatoFilterMixin:
    """Generic filter mixin to provide basic search fields and an overrideable
    method for getting the search term."""

    search_fields: Iterable[Union[str, StringAgg]] = ("sid",)

    search_regex: Optional[re.Pattern] = None

    def get_search_term(self, value):
        value = value.strip()
        if self.search_regex:
            match = self.search_regex.search(value)
            if match:
                terms = list(match.groups())
                terms.extend(
                    [value[: match.start()].strip(), value[match.end() :].strip()],
                )
                return " ".join(terms)
        return value

    def search_queryset(self, queryset, search_term):
        search_term = self.get_search_term(search_term)
        return queryset.annotate(search=SearchVector(*self.search_fields)).filter(
            Q(
                search__icontains=search_term,
            )
            | Q(search=search_term),
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
        """Direct copy of the super function, which replaces the default form
        with the TamatoFilterForm."""
        fields = OrderedDict(
            [(name, filter_.field) for name, filter_ in self.filters.items()],
        )

        if not self.clear_url:
            raise NotImplementedError(
                f"clear_url must be defined on {self.__class__.__name__}",
            )
        fields["clear_url"] = self.clear_url

        form = TamatoFilterForm if self._meta.form == forms.Form else self._meta.form

        return type(str(f"{self.__class__.__name__}Form"), (form,), fields)


class ActiveStateMixin(FilterSet):
    """Generic filter mixin to provide an active state filter."""

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
        current_date = TaricDateRange(date.today(), date.today())
        if value == ["active"]:
            active_status_filter = Q(valid_between__upper_inf=True) | Q(
                valid_between__contains=current_date,
            )
        if value == ["terminated"]:
            active_status_filter = Q(valid_between__fully_lt=current_date)

        return queryset.filter(active_status_filter)


class StartYearMixin(FilterSet):
    """Generic filter mixin to provide an start year filter, providing the most
    recent 10 years."""

    current_year = date.today().year
    last_10_years = [
        Choice(str(year), str(year))
        for year in range(current_year, current_year - 10, -1)
    ]

    start_year = LazyMultipleChoiceFilter(
        choices=last_10_years,
        widget=forms.CheckboxSelectMultiple,
        method="filter_start_year",
        label="Start Year",
        help_text="Select all that apply",
        required=False,
    )

    def filter_start_year(self, queryset, name, value):
        if value:
            queryset = queryset.annotate(
                start_year=Extract(
                    StartDate("valid_between"),
                    "year",
                ),
            ).filter(start_year__in=value)
        return queryset


class AutoCompleteFilter(CharFilter):
    field_class = AutoCompleteField
