import logging

from django import forms
from django.contrib.postgres.aggregates import StringAgg
from django.urls import reverse_lazy
from django_filters import MultipleChoiceFilter

from common.filters import ActiveStateMixin
from common.filters import TamatoFilter
from common.filters import TamatoFilterBackend
from common.filters import TamatoFilterMixin
from geo_areas.models import GeographicalArea
from geo_areas.validators import AreaCode

log = logging.getLogger(__name__)


class GeographicalAreaFilterMixin(TamatoFilterMixin):
    """Filter mixin to allow custom filtering on descriptions, SIDs and
    area_codes, area_id."""

    search_fields = (
        "area_id",
        StringAgg("descriptions__description", delimiter=" "),
    )


class GeographicalAreaFilterBackend(TamatoFilterBackend, GeographicalAreaFilterMixin):
    pass


class GeographicalAreaFilter(
    TamatoFilter,
    GeographicalAreaFilterMixin,
    ActiveStateMixin,
):

    area_code = MultipleChoiceFilter(
        choices=AreaCode.choices,
        widget=forms.CheckboxSelectMultiple,
        label="Area code",
        help_text="Select all that apply",
        required=False,
    )

    clear_url = reverse_lazy("geo_area-ui-list")

    class Meta:
        model = GeographicalArea
        fields = ["search", "area_code", "active_state"]
