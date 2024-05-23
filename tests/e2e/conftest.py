import os

import pytest
from django.contrib.auth.models import Permission
from playwright.sync_api import Page
from pytest_django.live_server_helper import LiveServer

from common.tests import factories
from publishing.models import QueueState

from .utils import login

os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"


@pytest.fixture(scope="session")
def celery_config():
    return {
        "task_always_eager": False,
    }


@pytest.fixture
def tariff_manager_group():

    def set_permissions():
        for app_label, codename in [
            ("common", "add_trackedmodel"),
            ("common", "change_trackedmodel"),
            ("publishing", "manage_packaging_queue"),
            ("tasks", "add_userassignment"),
            ("workbaskets", "add_workbasket"),
            ("workbaskets", "view_workbasket"),
        ]:
            group.permissions.add(
                Permission.objects.get(
                    content_type__app_label=app_label,
                    codename=codename,
                ),
            )

    group = factories.UserGroupFactory.create(name="Tariff Managers")
    set_permissions()
    return group


@pytest.fixture
def user(tariff_manager_group):
    user = factories.UserFactory.create(username="test_user")
    user.set_password("password")
    user.save()
    tariff_manager_group.user_set.add(user)
    return user


@pytest.fixture
def empty_current_workbasket(user):
    workbasket = factories.WorkBasketFactory.create(author=user)
    workbasket.set_as_current(user)
    return workbasket


@pytest.fixture()
def paused_queue():
    return factories.OperationalStatusFactory(
        created_by=None,
        queue_state=QueueState.PAUSED,
    )


@pytest.fixture()
def unpaused_queue():
    return factories.OperationalStatusFactory(
        created_by=None,
        queue_state=QueueState.UNPAUSED,
    )


@pytest.fixture(scope="session")
def base_url(live_server: LiveServer):
    return live_server.url


@pytest.fixture
def page(live_server: LiveServer, page: Page, user):
    login(page, user, live_server.url)
    return page
