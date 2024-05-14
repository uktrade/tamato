import os

import pytest
from django.contrib.auth.models import Permission
from playwright.sync_api import Page
from pytest_django.live_server_helper import LiveServer

from common.tests import factories

from .utils import login

os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"


@pytest.fixture
def user():
    def add_permissions():
        for app_label, codename in [
            ("common", "add_trackedmodel"),
            ("workbaskets", "add_workbasket"),
            ("workbaskets", "view_workbasket"),
        ]:
            permission = Permission.objects.get(
                content_type__app_label=app_label,
                codename=codename,
            )
            user.user_permissions.add(permission)

    user = factories.UserFactory.create(username="test_user")
    user.set_password("password")
    user.save()
    add_permissions()
    return user


@pytest.fixture
def empty_current_workbasket(user):
    workbasket = factories.WorkBasketFactory.create(author=user)
    workbasket.set_as_current(user)
    return workbasket


@pytest.fixture(scope="session")
def base_url(live_server: LiveServer):
    return live_server.url


@pytest.fixture
def page(live_server: LiveServer, page: Page, user):
    login(page, user, live_server.url)
    return page
