import pytest
from django import forms

from workbaskets.forms import WorkbasketCreateForm

pytestmark = pytest.mark.django_db


class WorkBasketForm(forms.Form):
    title = forms.CharField()
    reason = forms.CharField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


def test_workbasket_form_validation():
    form = WorkBasketForm(
        {
            "title": "some title",
            "reason": "",
        },
    )
    assert not form.is_valid()
    assert "reason" in form.errors

    form = WorkBasketForm(
        {
            "title": "",
            "reason": "some reason",
        },
    )
    assert not form.is_valid()
    assert "title" in form.errors

    form = WorkBasketForm(
        {
            "title": "",
            "reason": "",
        },
    )
    assert not form.is_valid()
    assert "title" in form.errors
    assert "reason" in form.errors

    form = WorkBasketForm(
        {
            "title": "some title",
            "reason": "some reason",
        },
    )
    assert form.is_valid()


def test_workbasket_create_form_valid_data():
    """Test that WorkbasketCreateForm is valid when required fields in data."""
    data = {"title": "test basket", "reason": "testing testing"}
    form = WorkbasketCreateForm(data=data)

    assert form.is_valid()


def test_workbasket_create_form_invalid_data():
    """Test that WorkbasketCreateForm is not valid when required fields not in
    data."""
    form = WorkbasketCreateForm(data={})

    assert not form.is_valid()
    assert "This field is required." in form.errors["title"]
    assert "This field is required." in form.errors["reason"]
