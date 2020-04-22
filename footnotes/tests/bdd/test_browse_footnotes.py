"""Tests for browse footnotes behaviours."""
import pytest
from django.urls import reverse
from pytest_bdd import given
from pytest_bdd import scenarios
from pytest_bdd import then
from pytest_bdd import when

from common.tests.factories import FootnoteFactory

pytestmark = pytest.mark.django_db


scenarios("features/footnotes.feature")


@given("some footnotes exist")
def footnotes():
    return FootnoteFactory.create_batch(10)


@pytest.fixture
@when("I go to the footnotes page")
def footnotes_page(client):
    return client.get(reverse("footnotes-list"))


@then("I should see a list of footnotes")
def footnotes_list(footnotes, footnotes_page):
    assert all(
        footnote.description in footnotes_page.content.decode("utf8")
        for footnote in footnotes
    )
