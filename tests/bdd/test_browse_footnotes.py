import factory
import pytest
from django.urls import reverse
from pytest_bdd import given
from pytest_bdd import scenarios
from pytest_bdd import then
from pytest_bdd import when


@pytest.fixture(autouse=True)
def enable_db(db):
    pass


class FootnoteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "footnotes.Footnote"

    description = factory.Faker("paragraph")


scenarios("footnotes.feature")


@given("some footnotes exist")
def footnotes():
    return FootnoteFactory.create_batch(10)


@pytest.fixture
def response(client):
    return {}


@when("I go to the footnotes page")
def footnotes_page(footnotes, client, response):
    response["content"] = client.get(reverse("footnotes-list")).content.decode("utf-8")


@then("I should see a list of footnotes")
def footnotes_list(footnotes, response):
    assert all(footnote.description in response["content"] for footnote in footnotes)
