import pytest
from django import forms

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
