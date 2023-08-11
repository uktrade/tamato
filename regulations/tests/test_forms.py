import pytest
from django.utils import timezone

from common.tests import factories
from regulations import forms
from regulations.validators import RegulationUsage

pytestmark = pytest.mark.django_db


def test_regulation_create_form_creates_regulation(date_ranges, session_request):
    """Test that `RegulationCreateForm` generates `regulation_id` in
    `cleaned_data` and creates regulation instance."""
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
        "sequence_number": "123",
    }
    expected_regulation_id = f'{data["regulation_usage"][0]}{str(data["published_at_2"])[-2:]}{data["sequence_number"]:0>4}0'
    form = forms.RegulationCreateForm(data=data, request=session_request)

    assert form.is_valid()
    assert form.cleaned_data["regulation_id"]

    regulation = form.save(commit=False)
    assert regulation.regulation_group == group
    assert regulation.published_at == date_ranges.normal.lower
    assert regulation.regulation_id == expected_regulation_id
    assert regulation.approved == data["approved"]
    assert regulation.valid_between.lower == date_ranges.normal.lower


def test_regulation_create_form_missing_required_fields():
    """Test that `RegulationCreateForm` is invalid when required fields are
    missing in form data."""
    form = forms.RegulationCreateForm(data={})

    for field in [
        "regulation_group",
        "published_at",
        "approved",
        "start_date",
        "regulation_usage",
        "sequence_number",
    ]:
        assert form.fields[field].error_messages["required"] in form.errors[field]


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


def test_regulation_create_form_validate_approved_status(date_ranges, session_request):
    """Test that `RegulationCreateForm` is invalid when `approved=True` and
    `public_identifier`, `url` and `information_text` are missing in form
    data."""
    group = factories.RegulationGroupFactory.create()
    data = {
        "regulation_usage": RegulationUsage.PREFERENTIAL_TRADE_AGREEMENT,
        "public_identifier": "",
        "url": "",
        "information_text": "",
        "regulation_group": group.pk,
        "start_date_0": date_ranges.normal.lower.day,
        "start_date_1": date_ranges.normal.lower.month,
        "start_date_2": date_ranges.normal.lower.year,
        "published_at_0": date_ranges.normal.lower.day,
        "published_at_1": date_ranges.normal.lower.month,
        "published_at_2": date_ranges.normal.lower.year,
        "sequence_number": 1,
        "approved": True,
    }
    form = forms.RegulationCreateForm(data=data, request=session_request)

    assert not form.is_valid()
    assert "Enter a public identifier" in form.errors["public_identifier"]
    assert "Enter a URL" in form.errors["url"]
    assert "Enter a title" in form.errors["information_text"]


def test_regulation_create_form_invalid_part_value(date_ranges, session_request):
    """Test that RegulationCreateForm excepts an IndexError when looking for an
    alphanumeric character after Z and raises a ValidationError."""
    year = timezone.now().strftime("%y")
    factories.RegulationFactory.create(regulation_id=f"C{year}0001Z")
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


def test_regulation_edit_form_required_fields_draft():
    """Test that 'RegulationEditForm` is invalid when required fields are
    missing in form data for a draft regulation."""
    instance = factories.UIDraftRegulationFactory.create()
    form = form = forms.RegulationEditForm(data={}, instance=instance)
    for field in [
        "regulation_usage",
        "regulation_group",
        "start_date",
        "published_at",
        "sequence_number",
        "approved",
    ]:
        assert form.fields[field].error_messages["required"] in form.errors[field]


def test_regulation_edit_form_required_fields_non_draft():
    """Test that `RegulationEditForm` doesn't require `regulation_usage`,
    `published_at` and `sequence_number` when editing a non-draft regulation."""
    instance = factories.UIRegulationFactory.create()
    form_data = {
        "public_identifier": instance.public_identifier,
        "url": instance.url,
        "information_text": instance.information_text,
        "regulation_group": instance.regulation_group,
        "start_date_0": instance.valid_between.lower.day,
        "start_date_1": instance.valid_between.lower.month,
        "start_date_2": instance.valid_between.lower.year,
        "approved": True,
    }
    form = forms.RegulationEditForm(data=form_data, instance=instance)
    assert form.is_valid()


def test_regulation_edit_form_generates_regulation_id(date_ranges, session_request):
    """Test that `RegulationEditForm` generates new `regulation_id` if
    `regulation_usage`, `published_at` or `sequence_number` are edited for a
    draft regulation."""
    instance = factories.UIDraftRegulationFactory.create()
    form_data = {
        "regulation_usage": RegulationUsage.DRAFT_REGULATION,
        "regulation_group": instance.regulation_group,
        "start_date_0": instance.valid_between.lower.day,
        "start_date_1": instance.valid_between.lower.month,
        "start_date_2": instance.valid_between.lower.year,
        "published_at_0": instance.published_at.day,
        "published_at_1": instance.published_at.month,
        "published_at_2": instance.published_at.year,
        "sequence_number": "321",
        "approved": False,
    }
    publication_year = str(form_data["published_at_2"])[-2:]
    sequence_number = f"{form_data['sequence_number']:0>4}"

    form = forms.RegulationEditForm(
        data=form_data,
        instance=instance,
        request=session_request,
    )
    assert form.is_valid()

    regulation_usage = form_data["regulation_usage"][0]
    publication_year = str(form_data["published_at_2"])[-2:]
    sequence_number = f"{form_data['sequence_number']:0>4}"
    assert (
        form.cleaned_data["regulation_id"]
        == f"{regulation_usage}{publication_year}{sequence_number}0"
    )


def test_regulation_edit_form_validate_approved_status(session_request):
    """Test that `RegulationEditForm` is invalid when `approved=True` and
    `public_identifier`, `url` and `information_text` are missing in form
    data."""
    instance = factories.UIDraftRegulationFactory.create()
    sequence_number = instance.regulation_id[3:7]
    form_data = {
        "regulation_usage": RegulationUsage.PREFERENTIAL_TRADE_AGREEMENT,
        "public_identifier": "",
        "url": "",
        "information_text": "",
        "regulation_group": instance.regulation_group,
        "start_date_0": instance.valid_between.lower.day,
        "start_date_1": instance.valid_between.lower.month,
        "start_date_2": instance.valid_between.lower.year,
        "published_at_0": instance.published_at.day,
        "published_at_1": instance.published_at.month,
        "published_at_2": instance.published_at.year,
        "sequence_number": sequence_number,
        "approved": True,
    }
    form = forms.RegulationEditForm(
        data=form_data,
        instance=instance,
        request=session_request,
    )
    assert not form.is_valid()
    assert "Enter a public identifier" in form.errors["public_identifier"]
    assert "Enter a URL" in form.errors["url"]
    assert "Enter a title" in form.errors["information_text"]


def test_regulation_edit_form_unapproved_and_not_draft():
    """Test that RegulationEditForm raises a ValidationError when approved is
    False and instance regulation usage (first character of regulation_id) is
    anything other than DRAFT_REGULATION."""
    instance = factories.UIRegulationFactory.create()
    data = {
        "regulation_usage": RegulationUsage.PREFERENTIAL_TRADE_AGREEMENT,
        "public_identifier": instance.public_identifier,
        "url": instance.url,
        "information_text": instance.information_text,
        "regulation_group": instance.regulation_group,
        "start_date_0": instance.valid_between.lower.day,
        "start_date_1": instance.valid_between.lower.month,
        "start_date_2": instance.valid_between.lower.year,
        "published_at_0": instance.published_at.day,
        "published_at_1": instance.published_at.month,
        "published_at_2": instance.published_at.year,
        "sequence_number": 123,
        "approved": False,
    }
    form = forms.RegulationEditForm(data=data, instance=instance)
    assert not form.is_valid()
    assert (
        'Regulation status "Not approved" may only be applied when Regulation usage is "C: Draft regulation"'
        in form.errors["approved"]
    )
