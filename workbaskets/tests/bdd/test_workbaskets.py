import pytest
from pytest_bdd import given
from pytest_bdd import scenarios
from pytest_bdd import then
from pytest_bdd import when
from rest_framework.reverse import reverse

from common.tests import factories

pytestmark = pytest.mark.django_db


scenarios("features/workbaskets.feature")


@given('a valid user named "Alice"')
def valid_user():
    return factories.UserFactory.create(username="Alice")


@given("I am logged in as Alice")
def valid_user_login(client, valid_user):
    client.force_login(valid_user)


@given("I have a current workbasket")
def current_workbasket(valid_user):
    return factories.WorkBasketFactory.create(author=valid_user)


@pytest.fixture
@when("I view the main menu")
def main_menu(client):
    return client.get(reverse("index"))


@then("I see a notification that I have no current workbaskets")
def no_workbaskets(main_menu):
    response = main_menu.content.decode("utf-8")
    assert "You are not working with any workbaskets at the moment" in response


@then("I see a list of my current workbaskets")
def workbaskets_list(main_menu, current_workbasket):
    response = main_menu.content.decode("utf-8")
    assert "You have 1 workbasket, listed below" in response
