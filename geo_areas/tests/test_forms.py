import pytest

from common.models.transactions import Transaction
from common.models.utils import override_current_transaction
from common.tests import factories
from geo_areas import forms
from geo_areas.validators import AreaCode

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


def test_geographical_area_end_date_form_valid_date(date_ranges):
    geo_area = factories.GeographicalAreaFactory.create(
        valid_between=date_ranges.normal,
    )

    form_data = {
        "end_date_0": date_ranges.later.upper.day,
        "end_date_1": date_ranges.later.upper.month,
        "end_date_2": date_ranges.later.upper.year,
    }
    with override_current_transaction(Transaction.objects.last()):
        form = forms.GeographicalAreaEndDateForm(data=form_data, instance=geo_area)
        assert form.is_valid()


def test_geographical_area_end_date_form_invalid_date(date_ranges):
    geo_area = factories.GeographicalAreaFactory.create(
        valid_between=date_ranges.no_end,
    )
    order_origin_number = factories.QuotaOrderNumberOriginFactory.create(
        geographical_area=geo_area,
        valid_between=date_ranges.no_end,
    )

    invalid_date_1 = {
        "end_date_0": "z",
        "end_date_1": "z",
        "end_date_2": "zzzz",
    }
    form = forms.GeographicalAreaEndDateForm(data=invalid_date_1, instance=geo_area)
    assert not form.is_valid()

    invalid_date_2 = {
        "end_date_0": date_ranges.later.upper.day,
        "end_date_1": date_ranges.later.upper.month,
        "end_date_2": date_ranges.later.upper.year,
    }
    with override_current_transaction(Transaction.objects.last()):
        form = forms.GeographicalAreaEndDateForm(data=invalid_date_2, instance=geo_area)
        assert not form.is_valid()
        assert (
            "The end date must span the validity period of the quota order number origin that specifies this geographical area."
            in form.errors["end_date"]
        )


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
        form = forms.GeographicalAreaEditForm(data=form_data, instance=area_group)
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
        form = forms.GeographicalAreaEditForm(data=form_data, instance=area_group)
        assert not form.is_valid()
        assert "A start date is required." in form.errors["new_membership_start_date"]
        assert (
            "The end date must be the same as or before the area group's end date."
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
        form = forms.GeographicalAreaEditForm(
            data=country_form_data,
            instance=area_group,
        )
        assert not form.is_valid()
        assert (
            "The selected country or region is already a member of this area group."
            in form.errors["member"]
        )

        form = forms.GeographicalAreaEditForm(
            data=group_form_data,
            instance=country,
        )
        assert not form.is_valid()
        assert (
            "The selected area group already has this country or region as a member."
            in form.errors["geo_group"]
        )


def test_geographical_membership_edit_form_valid_deletion(
    date_ranges,
    session_with_workbasket,
):
    country = factories.CountryFactory.create()
    area_group = factories.GeoGroupFactory.create(valid_between=date_ranges.normal)
    membership = factories.GeographicalMembershipFactory.create(
        geo_group=area_group,
        member=country,
    )

    form_data = {
        "membership": membership.pk,
        "action": forms.GeoMembershipAction.DELETE,
    }

    with override_current_transaction(Transaction.objects.last()):
        form = forms.GeographicalAreaEditForm(
            data=form_data,
            instance=area_group,
            request=session_with_workbasket,
        )
        assert form.is_valid()


def test_geographical_membership_edit_form_invalid_deletion(
    date_ranges,
    session_with_workbasket,
):
    country = factories.CountryFactory.create()
    area_group = factories.GeoGroupFactory.create(valid_between=date_ranges.normal)
    membership = factories.GeographicalMembershipFactory.create(
        geo_group=area_group,
        member=country,
    )
    exclusion = factories.MeasureExcludedGeographicalAreaFactory.create(
        excluded_geographical_area=country,
    )

    form_data = {
        "membership": membership.pk,
        "action": forms.GeoMembershipAction.DELETE,
    }

    with override_current_transaction(Transaction.objects.last()):
        form = forms.GeographicalAreaEditForm(
            data=form_data,
            instance=area_group,
            request=session_with_workbasket,
        )
        assert not form.is_valid()
        assert (
            f"{membership.member.structure_description} is referenced as an excluded geographical area in a measure and cannot be deleted as a member of the area group."
            in form.errors["membership"]
        )


def test_geographical_membership_edit_form_valid_end_date(
    date_ranges,
    session_with_workbasket,
):
    country = factories.CountryFactory.create()
    area_group = factories.GeoGroupFactory.create(valid_between=date_ranges.normal)
    membership = factories.GeographicalMembershipFactory.create(
        geo_group=area_group,
        member=country,
    )

    form_data = {
        "membership": membership.pk,
        "action": forms.GeoMembershipAction.END_DATE,
        "membership_end_date_0": area_group.valid_between.upper.day,
        "membership_end_date_1": area_group.valid_between.upper.month,
        "membership_end_date_2": area_group.valid_between.upper.year,
    }

    with override_current_transaction(Transaction.objects.last()):
        form = forms.GeographicalAreaEditForm(
            data=form_data,
            instance=area_group,
            request=session_with_workbasket,
        )
        assert form.is_valid()


def test_geographical_membership_edit_form_invalid_end_date(
    date_ranges,
    session_with_workbasket,
):
    country = factories.CountryFactory.create()
    area_group = factories.GeoGroupFactory.create(valid_between=date_ranges.normal)
    membership = factories.GeographicalMembershipFactory.create(
        geo_group=area_group,
        member=country,
    )

    invalid_end_date_1 = {
        "membership": membership.pk,
        "action": forms.GeoMembershipAction.END_DATE,
        "membership_end_date_0": date_ranges.later.upper.day,
        "membership_end_date_1": date_ranges.later.upper.month,
        "membership_end_date_2": date_ranges.later.upper.year,
    }
    invalid_end_date_2 = {
        "membership": membership.pk,
        "action": forms.GeoMembershipAction.END_DATE,
        "membership_end_date_0": date_ranges.earlier.lower.day,
        "membership_end_date_1": date_ranges.earlier.lower.month,
        "membership_end_date_2": date_ranges.earlier.lower.year,
    }

    with override_current_transaction(Transaction.objects.last()):
        form = forms.GeographicalAreaEditForm(
            data=invalid_end_date_1,
            instance=area_group,
            request=session_with_workbasket,
        )
        assert not form.is_valid()
        assert (
            "The end date must be the same as or before the area group's end date."
            in form.errors["__all__"]
        )

        form = forms.GeographicalAreaEditForm(
            data=invalid_end_date_2,
            instance=area_group,
            request=session_with_workbasket,
        )
        assert not form.is_valid()
        assert (
            "The end date must be the same as or after the area group's start date."
            in form.errors["__all__"]
        )


@pytest.mark.parametrize(
    ("area_code", "area_id"),
    [
        (AreaCode.COUNTRY, "TC"),
        (AreaCode.GROUP, "1234"),
        (AreaCode.REGION, "TR"),
    ],
)
def test_geographical_area_create_form_valid_data(date_ranges, area_code, area_id):
    """Tests that GeographicalAreaCreateForm is valid when required fields are
    in data."""
    form_data = {
        "area_code": area_code,
        "area_id": area_id,
        "start_date_0": date_ranges.normal.lower.day,
        "start_date_1": date_ranges.normal.lower.month,
        "start_date_2": date_ranges.normal.lower.year,
        "end_date_0": date_ranges.normal.upper.day,
        "end_date_1": date_ranges.normal.upper.month,
        "end_date_2": date_ranges.normal.upper.year,
        "description": "Test",
    }
    form = forms.GeographicalAreaCreateForm(data=form_data)
    assert form.is_valid()


def test_geographical_area_create_form_invalid_data():
    """Tests that GeographicalAreaCreateForm is not valid when invalid data is
    used."""
    form_data = {
        "area_code": "2",
        "area_id": "abcd",
        "start_date_0": "2",
        "start_date_1": "2",
        "start_date_2": "2",
        "end_date_0": "1",
        "end_date_1": "1",
        "end_date_2": "1",
        "description": "<test>",
    }
    expected_form_errors = {
        "area_id": "Enter a geographical area ID in the correct format.",
        "end_date": "The end date must be the same as or after the start date.",
        "description": "Only symbols .,/()&£$@!+-% are allowed.",
    }

    form = forms.GeographicalAreaCreateForm(data=form_data)
    assert not form.is_valid()
    for field, message in expected_form_errors.items():
        assert message in form.errors[field]


def test_geographical_area_create_form_missing_data():
    """Tests that GeographicalAreaCreateForm is not valid when required fields
    are not in data."""
    empty_data = {}
    form = forms.GeographicalAreaCreateForm(data=empty_data)
    assert not form.is_valid()

    expected_form_errors = {
        "area_code": "Select an area code from the dropdown.",
        "area_id": "Enter a geographical area ID.",
        "start_date": "Enter the day, month and year",
        "description": "Enter a geographical area description.",
    }
    for field, message in expected_form_errors.items():
        assert message in form.errors[field]


def test_geographical_membership_group_form_valid_selection(date_ranges):
    """Tests that GeographicalMembershipGroupForm is valid when required fields
    are in data."""
    country = factories.CountryFactory.create(valid_between=date_ranges.no_end)
    geo_group = factories.GeoGroupFactory.create(valid_between=date_ranges.no_end)

    form_data = {
        "geo_group": geo_group.pk,
        "start_date_0": date_ranges.no_end.lower.day,
        "start_date_1": date_ranges.no_end.lower.month,
        "start_date_2": date_ranges.no_end.lower.year,
    }
    with override_current_transaction(Transaction.objects.last()):
        form = forms.GeographicalMembershipGroupForm(data=form_data, geo_area=country)
        assert form.is_valid()


def test_geographical_membership_group_form_invalid_selection(date_ranges):
    """Tests that GeographicalMembershipGroupForm is not valid when selection
    field contains invalid data."""
    country = factories.CountryFactory.create(valid_between=date_ranges.no_end)

    form_data = {
        "geo_group": "test",
    }
    with override_current_transaction(Transaction.objects.last()):
        form = forms.GeographicalMembershipGroupForm(data=form_data, geo_area=country)
        assert not form.is_valid()
        assert (
            "Select a valid choice. That choice is not one of the available choices."
            in form.errors["geo_group"]
        )


def test_geographical_membership_group_form_invalid_dates(date_ranges):
    """Tests that GeographicalMembershipGroupForm is not valid when date fields
    contain invalid data."""
    country = factories.CountryFactory.create(valid_between=date_ranges.normal)
    area_group = factories.GeoGroupFactory.create(valid_between=date_ranges.normal)

    form_data = {
        "geo_group": area_group.pk,
        "start_date_0": date_ranges.earlier.lower.day,
        "start_date_1": date_ranges.earlier.lower.month,
        "start_date_2": date_ranges.earlier.lower.year,
    }
    with override_current_transaction(Transaction.objects.last()):
        form = forms.GeographicalMembershipGroupForm(data=form_data, geo_area=country)
        assert not form.is_valid()
        assert "start_date" and "end_date" in form.errors.keys()


def test_geographical_membership_group_formset_same_selection(date_ranges):
    """Tests that GeographicalMembershipGroupFormSet is not valid when a
    geographical area has been selected more than once."""
    country = factories.CountryFactory.create(valid_between=date_ranges.no_end)
    area_group = factories.GeoGroupFactory.create(valid_between=date_ranges.no_end)

    form_data = {
        "geo_membership-group-formset-0-geo_group": area_group.pk,
        "geo_membership-group-formset-0-start_date_0": date_ranges.no_end.lower.day,
        "geo_membership-group-formset-0-start_date_1": date_ranges.no_end.lower.month,
        "geo_membership-group-formset-0-start_date_2": date_ranges.no_end.lower.year,
        "geo_membership-group-formset-1-geo_group": area_group.pk,
        "geo_membership-group-formset-1-start_date_0": date_ranges.no_end.lower.day,
        "geo_membership-group-formset-1-start_date_1": date_ranges.no_end.lower.month,
        "geo_membership-group-formset-1-start_date_2": date_ranges.no_end.lower.year,
    }
    with override_current_transaction(Transaction.objects.last()):
        formset = forms.GeographicalMembershipGroupFormSet(
            data=form_data,
            form_kwargs={"geo_area": country},
        )
        assert not formset.is_valid()
        assert (
            "The same area group cannot be selected more than once."
            in formset.non_form_errors()
        )


def test_geographical_membership_member_form_valid_selection(date_ranges):
    """Tests that GeographicalMembershipMemberForm is valid when required fields
    are in data."""
    geo_group = factories.GeoGroupFactory.create(valid_between=date_ranges.no_end)
    country = factories.CountryFactory.create(valid_between=date_ranges.no_end)

    form_data = {
        "member": country.pk,
        "start_date_0": date_ranges.no_end.lower.day,
        "start_date_1": date_ranges.no_end.lower.month,
        "start_date_2": date_ranges.no_end.lower.year,
    }
    with override_current_transaction(Transaction.objects.last()):
        form = forms.GeographicalMembershipMemberForm(
            data=form_data,
            geo_area=geo_group,
        )
        assert form.is_valid()


def test_geographical_membership_member_form_invalid_selection(date_ranges):
    """Tests that GeographicalMembershipMemberForm is not valid when selection
    field contains invalid data."""
    geo_group = factories.GeoGroupFactory.create(valid_between=date_ranges.no_end)

    form_data = {
        "member": "test",
    }
    with override_current_transaction(Transaction.objects.last()):
        form = forms.GeographicalMembershipMemberForm(
            data=form_data,
            geo_area=geo_group,
        )
        assert not form.is_valid()
        assert (
            "Select a valid choice. That choice is not one of the available choices."
            in form.errors["member"]
        )


def test_geographical_membership_member_form_invalid_dates(date_ranges):
    """Tests that GeographicalMembershipMemberForm is not valid when date fields
    contain invalid data."""
    country = factories.CountryFactory.create(valid_between=date_ranges.normal)
    area_group = factories.GeoGroupFactory.create(valid_between=date_ranges.normal)

    form_data = {
        "member": country.pk,
        "start_date_0": date_ranges.earlier.lower.day,
        "start_date_1": date_ranges.earlier.lower.month,
        "start_date_2": date_ranges.earlier.lower.year,
    }
    with override_current_transaction(Transaction.objects.last()):
        form = forms.GeographicalMembershipMemberForm(
            data=form_data,
            geo_area=area_group,
        )
        assert not form.is_valid()
        assert "start_date" and "end_date" in form.errors.keys()


def test_geographical_membership_member_formset_same_selection(date_ranges):
    """Tests that GeographicalMembershipMemberFormSet is not valid when a
    geographical area has been selected more than once."""
    country = factories.CountryFactory.create(valid_between=date_ranges.no_end)
    area_group = factories.GeoGroupFactory.create(valid_between=date_ranges.no_end)

    form_data = {
        "geo_membership-member-formset-0-member": country.pk,
        "geo_membership-member-formset-0-start_date_0": date_ranges.no_end.lower.day,
        "geo_membership-member-formset-0-start_date_1": date_ranges.no_end.lower.month,
        "geo_membership-member-formset-0-start_date_2": date_ranges.no_end.lower.year,
        "geo_membership-member-formset-1-member": country.pk,
        "geo_membership-member-formset-1-start_date_0": date_ranges.no_end.lower.day,
        "geo_membership-member-formset-1-start_date_1": date_ranges.no_end.lower.month,
        "geo_membership-member-formset-1-start_date_2": date_ranges.no_end.lower.year,
    }
    with override_current_transaction(Transaction.objects.last()):
        formset = forms.GeographicalMembershipMemberFormSet(
            data=form_data,
            form_kwargs={"geo_area": area_group},
        )
        assert not formset.is_valid()
        assert (
            "The same country or region cannot be selected more than once."
            in formset.non_form_errors()
        )
