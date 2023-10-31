"""Tests for view footnotes behaviours."""
import pytest
from django.urls import reverse
from pytest_bdd import scenarios
from pytest_bdd import then
from pytest_bdd import when

from common.models.utils import override_current_transaction

pytestmark = pytest.mark.django_db

scenarios("features/detail-footnotes.feature")


@pytest.fixture
@when("I select footnote NC000")
def footnote_detail(client, footnote_NC000):
    return client.get(footnote_NC000.get_url())


@pytest.fixture
@when("I select footnote NC000")
def footnote_descriptions(client, footnote_NC000):
    url = reverse(
        "footnote-ui-detail-descriptions",
        kwargs={
            "footnote_type__footnote_type_id": footnote_NC000.footnote_type.footnote_type_id,
            "footnote_id": footnote_NC000.footnote_id,
        },
    )
    return client.get(url)


@then("a summary of the core information should be presented")
def footnote_core_data(footnote_detail, footnote_NC000):
    content = footnote_detail.content.decode()
    f = footnote_NC000
    ft = f.footnote_type

    assert str(f) in content
    with override_current_transaction(f.transaction):
        assert f.get_description().description in content
    assert str(ft) in content
    assert f"{f.valid_between.lower:%d %b %Y}" in content


@then("the descriptions against the footnote should be presented")
def footnote_description_data(footnote_descriptions, footnote_NC000):
    content = footnote_descriptions.content.decode()
    f = footnote_NC000

    for description in f.descriptions.all():
        assert description.description in content
        assert f"{description.validity_start:%d %b %Y}" in content
