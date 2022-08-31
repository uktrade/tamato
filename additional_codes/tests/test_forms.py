import pytest

from additional_codes import forms
from common.tests import factories

pytestmark = pytest.mark.django_db

# https://uktrade.atlassian.net/browse/TP2000-296
def test_additional_code_create_sid(session_with_workbasket, date_ranges):
    """Tests that additional code type is NOT considered when generating a new
    sid."""
    type_1 = factories.AdditionalCodeTypeFactory.create()
    type_2 = factories.AdditionalCodeTypeFactory.create()
    additional_code = factories.AdditionalCodeFactory.create(type=type_1)
    data = {
        "type": type_2,
        "code": 123,
        "description": "description",
        "start_date_0": date_ranges.normal.lower.day,
        "start_date_1": date_ranges.normal.lower.month,
        "start_date_2": date_ranges.normal.lower.year,
    }
    form = forms.AdditionalCodeCreateForm(data=data, request=session_with_workbasket)

    assert form.is_valid()

    new_additional_code = form.save(commit=False)

    assert new_additional_code.sid != additional_code.sid


def test_additional_code_create_valid_data(session_with_workbasket, date_ranges):
    """Tests that AdditionalCodeCreateForm.is_valid() returns True when passed
    required fields and additional_code_description values in cleaned data."""
    code_type = factories.AdditionalCodeTypeFactory.create()
    data = {
        "type": code_type.pk,
        "code": 123,
        "description": "description",
        "start_date_0": date_ranges.normal.lower.day,
        "start_date_1": date_ranges.normal.lower.month,
        "start_date_2": date_ranges.normal.lower.year,
    }
    form = forms.AdditionalCodeCreateForm(data=data, request=session_with_workbasket)

    assert form.is_valid()
    assert form.cleaned_data["additional_code_description"].description == "description"
    assert (
        form.cleaned_data["additional_code_description"].validity_start
        == date_ranges.normal.lower
    )


def test_additional_code_form_valid_instance(date_ranges):
    """Tests that AdditionalCodeForm.is_valid() returns True when passed code
    instance and required fields, while sid and type fields are in cleaned
    data."""
    code = factories.AdditionalCodeFactory.create()
    data = {
        "start_date_0": date_ranges.normal.lower.day,
        "start_date_1": date_ranges.normal.lower.month,
        "start_date_2": date_ranges.normal.lower.year,
    }
    form = forms.AdditionalCodeForm(data=data, instance=code)

    assert form.is_valid()
    assert form.cleaned_data["sid"] == code.sid
    assert form.cleaned_data["type"] == code.type


def test_additional_code_form_valid_no_instance(date_ranges):
    """Tests that AdditionalCodeForm.is_valid() returns True when passed
    required fields without a code instance."""
    code_type = factories.AdditionalCodeTypeFactory.create()
    data = {
        "type": code_type.pk,
        "start_date_0": date_ranges.normal.lower.day,
        "start_date_1": date_ranges.normal.lower.month,
        "start_date_2": date_ranges.normal.lower.year,
    }
    form = forms.AdditionalCodeForm(data=data, instance=None)

    assert form.is_valid()


def test_additional_code_form_invalid():
    """Tests that AdditionalCode.is_valid() returns False when missing required
    fields."""
    form = forms.AdditionalCodeForm(data={}, instance=None)

    assert not form.is_valid()
    assert "Enter the day, month and year" in form.errors["start_date"]
