import pytest

from common.tests import factories
from geo_areas import forms

pytestmark = pytest.mark.django_db


def test_geographical_area_create_description_form_valid_data(date_ranges):
    """Test that GeographicalAreaCreateDescriptionForm is valid when required
    fields in data."""
    geo_area = factories.GeographicalAreaFactory.create()
    data = {
        "described_geographicalarea": geo_area.pk,
        "description": "description",
        "validity_start_0": date_ranges.normal.lower.day,
        "validity_start_1": date_ranges.normal.lower.month,
        "validity_start_2": date_ranges.normal.lower.year,
    }
    form = forms.GeographicalAreaCreateDescriptionForm(data=data)

    assert form.is_valid()


def test_geographical_area_create_description_form_invalid_data():
    """Test that GeographicalAreaCreateDescriptionForm is not valid when
    required fields not in data."""
    form = forms.GeographicalAreaCreateDescriptionForm(data={})

    assert not form.is_valid()
    assert "This field is required." in form.errors["described_geographicalarea"]
    assert "This field is required." in form.errors["description"]
    assert "Enter the day, month and year" in form.errors["validity_start"]


def test_geographical_area_end_date_form_valid(date_ranges):
    geo_area = factories.GeographicalAreaFactory.create(
        valid_between=date_ranges.normal,
    )

    form_data = {
        "end_date_0": date_ranges.later.upper.day,
        "end_date_1": date_ranges.later.upper.month,
        "end_date_2": date_ranges.later.upper.year,
    }
    form = forms.GeographicalAreaEndDateForm(data=form_data, instance=geo_area)

    assert form.is_valid()


def test_geographical_area_end_date_form_invalid(date_ranges):
    geo_area = factories.GeographicalAreaFactory.create(
        valid_between=date_ranges.normal,
    )

    form_data = {
        "end_date_0": "z",
        "end_date_1": "z",
        "end_date_2": "zzzz",
    }
    form = forms.GeographicalAreaEndDateForm(data=form_data, instance=geo_area)

    assert not form.is_valid()
