import pytest

from common.models.transactions import Transaction
from common.models.utils import override_current_transaction
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


def test_geographical_area_create_description_form_missing_required_fields():
    """Test that GeographicalAreaCreateDescriptionForm is not valid when
    required fields not in data."""
    form = forms.GeographicalAreaCreateDescriptionForm(data={})

    assert not form.is_valid()
    assert "This field is required." in form.errors["described_geographicalarea"]
    assert "This field is required." in form.errors["description"]
    assert "Enter the day, month and year" in form.errors["validity_start"]


def test_geographical_area_create_description_form_invalid_description(date_ranges):
    """Test that GeographicalAreaCreateDescriptionForm is not valid when
    restricted characters are used."""
    geo_area = factories.GeographicalAreaFactory.create()
    data = {
        "described_geographicalarea": geo_area.pk,
        "description": "<bad_code></script>",
        "validity_start_0": date_ranges.normal.lower.day,
        "validity_start_1": date_ranges.normal.lower.month,
        "validity_start_2": date_ranges.normal.lower.year,
        "validity_start_2": date_ranges.normal.lower.year,
    }
    form = forms.GeographicalAreaCreateDescriptionForm(data=data)

    assert not form.is_valid()
    assert "Only symbols .,/()&£$@!+-% are allowed." in form.errors["description"]


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


def test_geographical_membership_add_form_valid_data(date_ranges):
    country = factories.CountryFactory.create()
    area_group = factories.GeoGroupFactory.create(valid_between=date_ranges.normal)

    form_data = {
        "member": "COUNTRY",
        "country": country.pk,
        "new_membership_start_date_0": area_group.valid_between.lower.day,
        "new_membership_start_date_1": area_group.valid_between.lower.month,
        "new_membership_start_date_2": area_group.valid_between.lower.year,
        "new_membership_end_date_0": area_group.valid_between.upper.day,
        "new_membership_end_date_1": area_group.valid_between.upper.month,
        "new_membership_end_date_2": area_group.valid_between.upper.year,
    }
    with override_current_transaction(Transaction.objects.last()):
        form = forms.GeographicalMembershipAddForm(data=form_data, instance=area_group)
        assert form.is_valid()


def test_geographical_membership_add_form_invalid_dates(date_ranges):
    country = factories.CountryFactory.create()
    area_group = factories.GeoGroupFactory.create(valid_between=date_ranges.normal)
    membership = factories.GeographicalMembershipFactory.create(
        geo_group=area_group,
        member=country,
    )

    form_data = {
        "member": "COUNTRY",
        "country": country.pk,
        "new_membership_end_date_0": area_group.valid_between.upper.day + 1,
        "new_membership_end_date_1": area_group.valid_between.upper.month + 1,
        "new_membership_end_date_2": area_group.valid_between.upper.year + 1,
    }
    with override_current_transaction(Transaction.objects.last()):
        form = forms.GeographicalMembershipAddForm(data=form_data, instance=area_group)
        assert not form.is_valid()
        assert "A start date is required." in form.errors["new_membership_start_date"]
        assert (
            "The end date must be within the validity period of the area group."
            in form.errors["new_membership_end_date"]
        )


def test_geographical_membership_add_form_invalid_selection(date_ranges):
    country = factories.CountryFactory.create()
    area_group = factories.GeoGroupFactory.create(valid_between=date_ranges.normal)
    membership = factories.GeographicalMembershipFactory.create(
        geo_group=area_group,
        member=country,
    )

    country_form_data = {
        "member": "COUNTRY",
        "country": country.pk,
    }
    group_form_data = {
        "geo_group": area_group.pk,
    }

    with override_current_transaction(Transaction.objects.last()):
        form = forms.GeographicalMembershipAddForm(
            data=country_form_data,
            instance=area_group,
        )
        assert not form.is_valid()
        assert (
            "The selected country or region is already a member of this area group."
            in form.errors["member"]
        )

        form = forms.GeographicalMembershipAddForm(
            data=group_form_data,
            instance=country,
        )
        assert not form.is_valid()
        assert (
            "The selected area group already has this country or region as a member."
            in form.errors["geo_group"]
        )
