from django.db.models import Q
from django.forms import CheckboxSelectMultiple
from django.urls import reverse_lazy

from common.filters import ActiveStateMixin
from common.filters import LazyMultipleChoiceFilter
from common.filters import StartYearMixin
from common.filters import TamatoFilter
from common.filters import TamatoFilterBackend
from common.filters import TamatoFilterMixin
from common.filters import type_choices
from regulations.models import Group
from regulations.models import Regulation
from regulations.validators import RegulationUsage


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
    class Meta:
        model = Regulation
        fields = [
            "search",
            "regulation_usage",
            "regulation_group",
            "approved",
            "start_year",
            "active_state",
        ]

    clear_url = reverse_lazy("regulation-ui-list")

    APPROVED_STATUS_CHOICES = (
        (True, "Approved"),
        (False, "Not approved"),
    )

    regulation_usage = LazyMultipleChoiceFilter(
        choices=RegulationUsage.choices[1:],
        widget=CheckboxSelectMultiple,
        method="filter_regulation_usage",
        label="Regulation usage",
        help_text="Select all that apply",
        required=False,
    )

    regulation_group = LazyMultipleChoiceFilter(
        choices=type_choices(Group.objects.latest_approved()),
        widget=CheckboxSelectMultiple,
        field_name="regulation_group__group_id",
        label="Regulation group",
        help_text="Select all that apply",
        required=False,
    )

    approved = LazyMultipleChoiceFilter(
        choices=APPROVED_STATUS_CHOICES,
        widget=CheckboxSelectMultiple,
        field_name="approved",
        label="Status of the legislation",
        help_text="Select all that apply",
        required=False,
    )

    def filter_regulation_usage(self, queryset, name, value):
        regulation_usage_filter = Q()
        for usage_key in value:
            regulation_usage_filter |= Q(regulation_id__startswith=usage_key)
        return queryset.filter(regulation_usage_filter)
