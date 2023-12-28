import pytest
from bs4 import BeautifulSoup
from django.urls import reverse

from common.models.transactions import Transaction
from common.models.utils import override_current_transaction
from common.tests import factories
from quotas import forms
from quotas import validators

pytestmark = pytest.mark.django_db


def test_update_quota_form_safeguard_invalid():
    """When a QuotaOrderNumber with the category safeguard is edited the
    category cannot be changed."""
    quota = factories.QuotaOrderNumberFactory.create(
        category=validators.QuotaCategory.SAFEGUARD,
    )
    data = {
        "category": validators.QuotaCategory.WTO.value,
        "start_date_0": 1,
        "start_date_1": 1,
        "start_date_2": 2000,
    }
    with override_current_transaction(quota.transaction):
        form = forms.QuotaUpdateForm(data=data, instance=quota, initial={})
        assert not form.is_valid()
        assert "Please select a valid category" in form.errors["category"]


def test_update_quota_form_safeguard_disabled(valid_user_client_workbasket):
    """When a QuotaOrderNumber with the category safeguard is edited the
    category cannot be changed and the form field is disabled."""
    quota = factories.QuotaOrderNumberFactory.create(
        category=validators.QuotaCategory.SAFEGUARD,
    )
    response = valid_user_client_workbasket.get(
        reverse("quota-ui-edit", kwargs={"sid": quota.sid}),
    )
    html = response.content.decode(response.charset)
    soup = BeautifulSoup(html, "html.parser")
    assert "disabled" in soup.find(id="id_category").attrs.keys()


def test_quota_definition_errors(date_ranges):
    quota_definition = factories.QuotaDefinitionFactory.create(
        valid_between=date_ranges.big_no_end,
    )
    measurement_unit = factories.MeasurementUnitFactory()

    data = {
        "start_date_0": date_ranges.normal.lower.day,
        "start_date_1": date_ranges.normal.lower.month,
        "start_date_2": date_ranges.normal.lower.year,
        "end_date_0": date_ranges.normal.upper.day,
        "end_date_1": date_ranges.normal.upper.month,
        "end_date_2": date_ranges.normal.upper.year,
        "description": "Lorem ipsum.",
        "volume": "foo",
        "initial_volume": "bar",
        "measurement_unit": measurement_unit.pk,
        "measurement_unit_qualifier": "",
        "quota_critical_threshold": "foo",
        "quota_critical": "",
    }

    tx = Transaction.objects.last()

    def check_error_messages(form):
        assert not form.is_valid()
        assert form.errors["volume"][0] == "Volume must be a number"
        assert form.errors["initial_volume"][0] == "Initial volume must be a number"
        assert (
            form.errors["quota_critical_threshold"][0]
            == "Critical threshold must be a number"
        )
        assert form.errors["quota_critical"][0] == "Critical state must be set"

    with override_current_transaction(tx):
        form = forms.QuotaDefinitionUpdateForm(data=data, instance=quota_definition)
        check_error_messages(form)

    with override_current_transaction(tx):
        form = forms.QuotaDefinitionCreateForm(data=data)
        check_error_messages(form)


def test_quota_definition_volume_validation(date_ranges):
    quota_definition = factories.QuotaDefinitionFactory.create(
        valid_between=date_ranges.big_no_end,
    )
    measurement_unit = factories.MeasurementUnitFactory()

    data = {
        "start_date_0": date_ranges.normal.lower.day,
        "start_date_1": date_ranges.normal.lower.month,
        "start_date_2": date_ranges.normal.lower.year,
        "end_date_0": date_ranges.normal.upper.day,
        "end_date_1": date_ranges.normal.upper.month,
        "end_date_2": date_ranges.normal.upper.year,
        "description": "Lorem ipsum.",
        "volume": "600.000",
        "initial_volume": "500.000",
        "measurement_unit": measurement_unit.pk,
        "measurement_unit_qualifier": "",
        "quota_critical_threshold": "90",
        "quota_critical": "False",
    }

    tx = Transaction.objects.last()

    with override_current_transaction(tx):
        form = forms.QuotaDefinitionUpdateForm(data=data, instance=quota_definition)
        assert not form.is_valid()
        assert (
            form.errors["__all__"][0]
            == "Current volume cannot be higher than initial volume"
        )

    with override_current_transaction(tx):
        form = forms.QuotaDefinitionCreateForm(data=data)
        assert not form.is_valid()
        assert (
            form.errors["__all__"][0]
            == "Current volume cannot be higher than initial volume"
        )
