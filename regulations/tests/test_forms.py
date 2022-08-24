import pytest

from common.tests import factories
from regulations import forms
from regulations.validators import RegulationUsage

pytestmark = pytest.mark.django_db


def test_regulation_create_form_valid_data(date_ranges, session_request):
    """Test that RegulationCreateForm is valid when required fields in data and
    generates regulation_id in cleaned data."""
    group = factories.RegulationGroupFactory.create()
    data = {
        "regulation_group": group.pk,
        "published_at_0": date_ranges.normal.lower.day,
        "published_at_1": date_ranges.normal.lower.month,
        "published_at_2": date_ranges.normal.lower.year,
        "approved": False,
        "start_date_0": date_ranges.normal.lower.day,
        "start_date_1": date_ranges.normal.lower.month,
        "start_date_2": date_ranges.normal.lower.year,
        "regulation_usage": RegulationUsage.DRAFT_REGULATION,
        "sequence_number": 1,
    }
    form = forms.RegulationCreateForm(data=data, request=session_request)

    assert form.is_valid()
    assert form.cleaned_data["regulation_id"]


def test_regulation_create_form_unapproved_and_not_draft(date_ranges, session_request):
    """Test that RegulationCreateForm raises a ValidationError when approved is
    False and regulation_usage is anything other than DRAFT_REGULATION."""
    group = factories.RegulationGroupFactory.create()
    data = {
        "regulation_group": group.pk,
        "published_at_0": date_ranges.normal.lower.day,
        "published_at_1": date_ranges.normal.lower.month,
        "published_at_2": date_ranges.normal.lower.year,
        "approved": False,
        "start_date_0": date_ranges.normal.lower.day,
        "start_date_1": date_ranges.normal.lower.month,
        "start_date_2": date_ranges.normal.lower.year,
        "regulation_usage": RegulationUsage.PREFERENTIAL_TRADE_AGREEMENT,
        "sequence_number": 1,
    }
    form = forms.RegulationCreateForm(data=data, request=session_request)

    assert not form.is_valid()
    assert (
        'Regulation status "Not approved" may only be applied when Regulation usage is "C: Draft regulation"'
        in form.errors["approved"]
    )


def test_regulation_create_form_invalid_part_value(date_ranges, session_request):
    """Test that RegulationCreateForm excepts an IndexError when looking for an
    alphanumeric character after Z and raises a ValidationError."""
    factories.RegulationFactory.create(regulation_id="C220001Z")
    group = factories.RegulationGroupFactory.create()
    data = {
        "regulation_group": group.pk,
        "published_at_0": date_ranges.normal.lower.day,
        "published_at_1": date_ranges.normal.lower.month,
        "published_at_2": date_ranges.normal.lower.year,
        "approved": False,
        "start_date_0": date_ranges.normal.lower.day,
        "start_date_1": date_ranges.normal.lower.month,
        "start_date_2": date_ranges.normal.lower.year,
        "regulation_usage": RegulationUsage.DRAFT_REGULATION,
        "sequence_number": 1,
    }
    form = forms.RegulationCreateForm(data=data, request=session_request)

    assert not form.is_valid()
    assert (
        "Exceeded maximum number of parts for this regulation."
        in form.errors["__all__"]
    )


def test_regulation_edit_form_valid_data(date_ranges):
    """Test that RegulationEditForm is valid when required fields in data and
    uses instance regulation_id to generate cleaned data."""
    group = factories.RegulationGroupFactory.create()
    instance = factories.RegulationFactory.create(regulation_id="C220001Z")
    initial = {"published_at": date_ranges.normal.lower}
    data = {
        "regulation_group": group.pk,
        "approved": False,
        "start_date_0": date_ranges.normal.lower.day,
        "start_date_1": date_ranges.normal.lower.month,
        "start_date_2": date_ranges.normal.lower.year,
    }
    form = forms.RegulationEditForm(data=data, initial=initial, instance=instance)

    assert form.is_valid()
    assert form.cleaned_data["regulation_id"] == instance.regulation_id


def test_regulation_edit_form_unapproved_and_not_draft(date_ranges):
    """Test that RegulationEditForm raises a ValidationError when approved is
    False and instance regulation usage (first character of regulation_id) is
    anything other than DRAFT_REGULATION."""
    group = factories.RegulationGroupFactory.create()
    instance = factories.RegulationFactory.create()
    initial = {"published_at": date_ranges.normal.lower}
    data = {
        "regulation_group": group.pk,
        "approved": False,
        "start_date_0": date_ranges.normal.lower.day,
        "start_date_1": date_ranges.normal.lower.month,
        "start_date_2": date_ranges.normal.lower.year,
    }
    form = forms.RegulationEditForm(data=data, initial=initial, instance=instance)

    assert not form.is_valid()
    assert (
        'Regulation status "Not approved" may only be applied when Regulation usage is "C: Draft regulation"'
        in form.errors["approved"]
    )
