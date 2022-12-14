from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from django.urls import reverse
from django.utils.timezone import localtime
from common.tests import factories
from common.tests.factories import GeographicalAreaFactory
from common.tests.factories import GoodsNomenclatureFactory
from common.tests.factories import MeasureFactory
from checks.tests.factories import TrackedModelCheckFactory
from common.models.utils import override_current_transaction
from publishing import models

pytestmark = pytest.mark.django_db

def test_packaged_workbasket_create_user_not_logged_in_dev_sso_disabled(client, settings):
    """Tests that, when a user who hasn't logged in tries to create a workbasket
    in the dev env with SSO disabled, they are redirected to the login page."""
    settings.ENV = "dev"
    settings.SSO_ENABLED = False
    settings.LOGIN_URL = reverse("login")
    if "authbroker_client.middleware.ProtectAllViewsMiddleware" in settings.MIDDLEWARE:
        settings.MIDDLEWARE.remove(
            "authbroker_client.middleware.ProtectAllViewsMiddleware",
        )
    create_url = reverse("publishing:packaged-workbasket-queue-ui-create")
    form_data = {
        "theme": "My theme",
        "jira_url": "www.fakejiraticket.com",
    }
    response = client.post(create_url, form_data)

    assert response.status_code == 302
    assert response.url == f"{settings.LOGIN_URL}?next={create_url}"

def test_packaged_workbasket_create_without_permission(client):
    """Tests that WorkBasketCreate returns 403 to user without add_workbasket
    permission."""
    create_url = reverse("publishing:packaged-workbasket-queue-ui-create")
    form_data = {
        "theme": "My theme",
        "jira_url": "www.fakejiraticket.com",
    }
    user = factories.UserFactory.create()
    client.force_login(user)
    response = client.post(create_url, form_data)

    assert response.status_code == 403

def test_packaged_workbasket_create_form_no_business_rules(valid_user_api_client,session_workbasket):
    create_url = reverse("publishing:packaged-workbasket-queue-ui-create")

    form_data = {
        "theme": "My theme",
        "jira_url": "www.fakejiraticket.com",
    }

    response = valid_user_api_client.post(create_url, form_data)
    #  get the workbasket we have made, and make sure it matches title and description
    assert not models.PackagedWorkBasket.objects.select_related().filter(
        workbasket= session_workbasket.pk
    ).exists()

    assert response.status_code == 302
    response_url = f"/workbaskets/{session_workbasket.pk}/"
    # Only compare the response URL up to the query string.
    assert response.url[: len(response_url)] == response_url

@pytest.fixture
def setup(session_workbasket, valid_user_client):
    with session_workbasket.new_transaction() as transaction:
        good = GoodsNomenclatureFactory.create(transaction=transaction)
        measure = MeasureFactory.create(transaction=transaction)
        geo_area = GeographicalAreaFactory.create(transaction=transaction)
        objects = [good, measure, geo_area]
        for obj in objects:
            TrackedModelCheckFactory.create(
                transaction_check__transaction=transaction,
                model=obj,
                successful=True,
            )
    # session = valid_user_client.session
    # session["workbasket"] = {
    #     **session_workbasket,
    #     "id": session_workbasket.pk,
    #     "status": session_workbasket.status,
    #     "title": session_workbasket.title,
    #     "error_count": session_workbasket.tracked_model_check_errors.count(),
    # }
    # session.save()

def test_packaged_workbasket_create_form(valid_user_api_client,session_workbasket):
    # creating a packaged workbasket in the queue
    first_packaged_work_basket = factories.PackagedWorkBasketFactory()
    create_url = reverse("publishing:packaged-workbasket-queue-ui-create")

    form_data = {
        "theme": "My theme",
        "jira_url": "www.fakejiraticket.com",
    }

    response = valid_user_api_client.post(create_url, form_data)
    #  get the workbasket we have made, and make sure it matches title and description
    second_packaged_work_basket = models.PackagedWorkBasket.objects.select_related().filter(
        workbasket= session_workbasket.pk
    )[0]

    response_url = f"/publishing/{second_packaged_work_basket.id}/confirm-create/"
    # Only compare the response URL up to the query string.
    assert response.url[: len(response_url)] == response_url
    assert second_packaged_work_basket.theme == form_data["theme"]
    assert second_packaged_work_basket.jira_url == form_data["jira_url"]

    assert first_packaged_work_basket.position > 0
    assert first_packaged_work_basket.position < second_packaged_work_basket.position

def test_packaged_workbasket_create_form_business_rule_violations(valid_user_api_client,session_workbasket):
    with session_workbasket.new_transaction() as transaction:
        measure = MeasureFactory.create(transaction=transaction)
        TrackedModelCheckFactory.create(
                transaction_check__transaction=transaction,
                model=measure,
                successful=False,
            )
    create_url = reverse("publishing:packaged-workbasket-queue-ui-create")

    form_data = {
        "theme": "My theme",
        "jira_url": "www.fakejiraticket.com",
    }

    response = valid_user_api_client.post(create_url, form_data)
    #  get the workbasket we have made, and make sure it matches title and description
    assert not models.PackagedWorkBasket.objects.select_related().filter(
        workbasket= session_workbasket.pk
    ).exists()

    assert response.status_code == 302
    response_url = f"/workbaskets/{session_workbasket.pk}/"
    # Only compare the response URL up to the query string.
    assert response.url[: len(response_url)] == response_url


def test_create_duplicate_awaiting_instances(valid_user_api_client,session_workbasket):
    """Test that a WorkBasket cannot enter the packaging queue more than
    once."""
    create_url = reverse("publishing:packaged-workbasket-queue-ui-create")

    form_data = {
        "theme": "My theme",
        "jira_url": "www.fakejiraticket.com",
    }

    response = valid_user_api_client.post(create_url, form_data)
    #  get the workbasket we have made, and make sure it matches title and description
    second_packaged_work_basket = models.PackagedWorkBasket.objects.select_related().filter(
        workbasket= session_workbasket.pk
    )[0]

    assert response.status_code == 302
    response_url = f"/publishing/{second_packaged_work_basket.id}/confirm-create/"
    # Only compare the response URL up to the query string.
    assert response.url[: len(response_url)] == response_url

    response = valid_user_api_client.post(create_url, form_data)
