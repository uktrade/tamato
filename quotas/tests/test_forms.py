import pytest
from bs4 import BeautifulSoup
from django.urls import reverse

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
    form = forms.QuotaUpdateForm(data=data, instance=quota)
    assert not form.is_valid()
    assert "Please select a valid category" in form.errors["category"]


def test_update_quota_form_safeguard_disabled(valid_user_client):
    """When a QuotaOrderNumber with the category safeguard is edited the
    category cannot be changed and the form field is disabled."""
    quota = factories.QuotaOrderNumberFactory.create(
        category=validators.QuotaCategory.SAFEGUARD,
    )
    response = valid_user_client.get(
        reverse("quota-ui-edit", kwargs={"sid": quota.sid}),
    )
    html = response.content.decode(response.charset)
    soup = BeautifulSoup(html, "html.parser")
    assert "disabled" in soup.find(id="id_category").attrs.keys()
