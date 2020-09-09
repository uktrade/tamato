import pytest
from pytest_bdd import given
from pytest_bdd import scenarios
from pytest_bdd import then
from pytest_bdd import when
from rest_framework.reverse import reverse

from common.tests import factories

pytestmark = pytest.mark.django_db


scenarios("features/workbaskets.feature")


@given("I have a current workbasket", target_fixture="current_workbasket")
def current_workbasket(a_valid_user_called_alice):
    return factories.WorkBasketFactory.create(author=a_valid_user_called_alice)


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
