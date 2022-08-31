import datetime

import factory
import pytest
from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError

from common.tests import factories
from common.tests.util import date_post_data
from common.tests.util import raises_if
from common.tests.util import validity_period_post_data
from common.util import TaricDateRange
from footnotes import forms
from footnotes import models

pytestmark = pytest.mark.django_db

# https://uktrade.atlassian.net/browse/TP-851
def test_form_save_creates_new_footnote_id_and_footnote_type_id_combo(
    session_with_workbasket,
):
    """Tests that when two non-overlapping footnotes of the same type are
    created that these are created with a different footnote_id, to avoid
    duplication of footnote_id and footnote_type_id combination e.g. TN001."""
    footnote_type = factories.FootnoteTypeFactory.create()
    valid_between = TaricDateRange(
        datetime.date(2021, 1, 1),
        datetime.date(2021, 12, 1),
    )
    earlier = factories.FootnoteFactory.create(
        footnote_type=footnote_type,
        valid_between=valid_between,
        footnote_id="001",
    )

    data = {
        "footnote_type": footnote_type.pk,
        "start_date_0": 2,
        "start_date_1": 2,
        "start_date_2": 2022,
        "description": "A note on feet",
    }
    form = forms.FootnoteCreateForm(data=data, request=session_with_workbasket)
    new_footnote = form.save(commit=False)

    assert earlier.footnote_id != new_footnote.footnote_id


@pytest.mark.parametrize(
    ("new_data", "expected_valid"),
    (
        (lambda data: {}, False),
        (
            lambda data: {
                "description": "Test description",
                "footnote_type": "CN",
                "valid_between": validity_period_post_data(
                    datetime.date.today(),
                    datetime.date.today() + relativedelta(months=+1),
                ),
                **date_post_data("start_date", datetime.date.today()),
                **factory.build(
                    dict,
                    footnote_id="001",
                    footnote_type=factories.FootnoteTypeFactory.create().pk,
                    description=factories.FootnoteDescriptionFactory.create().pk,
                    FACTORY_CLASS=factories.FootnoteFactory,
                ),
            },
            True,
        ),
    ),
)
def test_footnote_create_form(use_create_form, new_data, expected_valid):
    with raises_if(ValidationError, not expected_valid):
        use_create_form(models.Footnote, new_data)


def test_footnote_form_valid_data_with_instance(date_ranges):
    """Test that FootnoteForm is valid when passed required data and uses
    instance to populate cleaned data fields."""
    footnote = factories.FootnoteFactory.create()
    data = {
        "start_date_0": date_ranges.normal.lower.day,
        "start_date_1": date_ranges.normal.lower.month,
        "start_date_2": date_ranges.normal.lower.year,
    }
    form = forms.FootnoteForm(data=data, instance=footnote)

    assert form.is_valid()
    assert form.cleaned_data["footnote_id"] == footnote.footnote_id
    assert form.cleaned_data["footnote_type"] == footnote.footnote_type


def test_footnote_form_valid_data_without_instance(date_ranges):
    """Test that FootnoteForm is valid when passed required data and no
    instance."""
    footnote_type = factories.FootnoteTypeFactory.create()
    data = {
        "start_date_0": date_ranges.normal.lower.day,
        "start_date_1": date_ranges.normal.lower.month,
        "start_date_2": date_ranges.normal.lower.year,
        "footnote_type": footnote_type.pk,
    }
    form = forms.FootnoteForm(data=data, instance=None)

    assert form.is_valid()


def test_footnote_form_invalid_data():
    """Test that FootnoteForm is not valid when missing required fields."""
    form = forms.FootnoteForm(data={}, instance=None)

    assert not form.is_valid()
    assert "Enter the day, month and year" in form.errors["start_date"]
    assert "Footnote type is required" in form.errors["footnote_type"]


def test_footnote_description_form_valid_data(date_ranges):
    """Test that FootnoteDescriptionForm is valid when required fields in
    data."""
    data = {
        "description": "description",
        "validity_start_0": date_ranges.normal.lower.day,
        "validity_start_1": date_ranges.normal.lower.month,
        "validity_start_2": date_ranges.normal.lower.year,
    }
    form = forms.FootnoteDescriptionForm(data=data)

    assert form.is_valid()


def test_footnote_description_form_invalid_data():
    """Test that FootnoteDescriptionForm is not valid when missing required
    fields."""
    form = forms.FootnoteDescriptionForm(data={})

    assert not form.is_valid()
    assert "Enter the day, month and year" in form.errors["validity_start"]
    assert "This field is required." in form.errors["description"]
