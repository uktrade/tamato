import pytest

from workbaskets.forms import WorkbasketCreateForm

pytestmark = pytest.mark.django_db


def test_workbasket_form_validation():
    form = WorkbasketCreateForm(
        {
            "title": "some title",
            "reason": "",
        },
    )
    assert not form.is_valid()
    assert "title" in form.errors
    assert "reason" in form.errors

    form = WorkbasketCreateForm(
        {
            "title": "",
            "reason": "some reason",
        },
    )
    assert not form.is_valid()
    assert "title" in form.errors

    form = WorkbasketCreateForm(
        {
            "title": "some title",
            "reason": "some reason",
        },
    )
    assert not form.is_valid()
    assert "title" in form.errors


def test_workbasket_create_form_valid_data():
    """Test that WorkbasketCreateForm is valid when required fields in data."""
    data = {"title": "123", "reason": "testing testing"}
    form = WorkbasketCreateForm(data=data)

    assert form.is_valid()


def test_workbasket_create_form_invalid_data():
    """Test that WorkbasketCreateForm is not valid when required fields not in
    data."""
    form = WorkbasketCreateForm(data={})

    assert not form.is_valid()
    assert "This field is required." in form.errors["title"]
    assert "This field is required." in form.errors["reason"]
