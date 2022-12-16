from unittest.mock import patch

import pytest
from django.conf import settings
from django.urls import reverse

from checks.tests.factories import TrackedModelCheckFactory
from checks.tests.factories import TransactionCheckFactory
from common.tests import factories
from common.tests.factories import GeographicalAreaFactory
from common.tests.factories import GoodsNomenclatureFactory
from common.tests.factories import MeasureFactory
from publishing import models
from workbaskets.validators import WorkflowStatus

pytestmark = pytest.mark.django_db


def test_packaged_workbasket_create_user_not_logged_in_dev_sso_disabled(
    client,
    settings,
):
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


def test_packaged_workbasket_create_form_no_business_rules( valid_user_client,session_workbasket):
    session = valid_user_client.session
    session["workbasket"] = {
        "id": session_workbasket.pk,
        "status": session_workbasket.status,
        "title": session_workbasket.title,
        "error_count": session_workbasket.tracked_model_check_errors.count(),
    }
    session.save()
    create_url = reverse("publishing:packaged-workbasket-queue-ui-create")

    form_data = {
        "theme": "My theme",
        "jira_url": "www.fakejiraticket.com",
    }

    response = valid_user_client.post(create_url, form_data)
    
    assert (
        not models.PackagedWorkBasket.objects.all_queued()
        .filter(
            workbasket=session_workbasket,
        )
        .exists()
    )

    assert response.status_code == 302
    response_url = f"/workbaskets/{session_workbasket.id}/"
    # Only compare the response URL up to the query string.
    assert response.url[: len(response_url)] == response_url

def test_packaged_workbasket_create_form( valid_user_client):
    workbasket = factories.WorkBasketFactory.create(
        status=WorkflowStatus.EDITING,
    )
    with workbasket.new_transaction() as transaction:
        TransactionCheckFactory.create(
            transaction=transaction,
            successful=True,
            completed=True,
        )

    session = valid_user_client.session
    session["workbasket"] = {
        "id": workbasket.pk,
        "status": workbasket.status,
        "title": workbasket.title,
        "error_count": workbasket.tracked_model_check_errors.count(),
    }
    session.save()
    # creating a packaged workbasket in the queue
    first_packaged_work_basket = factories.PackagedWorkBasketFactory()
    create_url = reverse("publishing:packaged-workbasket-queue-ui-create")

    form_data = {
        "theme": "My theme",
        "jira_url": "www.fakejiraticket.com",
    }

    response = valid_user_client.post(create_url, form_data)

    assert response.status_code == 302
    assert "/confirm-create/" in response.url
    #  get the workbasket we have made, and make sure it matches title and description
    second_packaged_work_basket = (
        models.PackagedWorkBasket.objects.all_queued()
        .filter(
            workbasket=workbasket.pk,
        )
        .get()
    )

    response_url = f"/publishing/{second_packaged_work_basket.id}/confirm-create/"
    # Only compare the response URL up to the query string.
    assert response.url[: len(response_url)] == response_url
    assert second_packaged_work_basket.theme == form_data["theme"]
    assert form_data["jira_url"] in second_packaged_work_basket.jira_url
    assert first_packaged_work_basket.position > 0
    assert first_packaged_work_basket.position < second_packaged_work_basket.position


def test_packaged_workbasket_create_form_business_rule_violations( valid_user_client):
    workbasket = factories.WorkBasketFactory.create(
        status=WorkflowStatus.EDITING,
    )
    with workbasket.new_transaction() as transaction:
        TransactionCheckFactory.create(
            transaction=transaction,
            successful=False,
            completed=True,
        )

    session = valid_user_client.session
    session["workbasket"] = {
        "id": workbasket.pk,
        "status": workbasket.status,
        "title": workbasket.title,
        "error_count": workbasket.tracked_model_check_errors.count(),
    }
    session.save()
    create_url = reverse("publishing:packaged-workbasket-queue-ui-create")

    form_data = {
        "theme": "My theme",
        "jira_url": "www.fakejiraticket.com",
    }

    response = valid_user_client.post(create_url, form_data)
    #  get the workbasket we have made, and make sure it matches title and description
    assert (
        not models.PackagedWorkBasket.objects.all_queued()
        .filter(
            workbasket=workbasket,
        )
        .exists()
    )

    assert response.status_code == 302
    response_url = f"/workbaskets/{workbasket.pk}/"
    # Only compare the response URL up to the query string.
    assert response.url[: len(response_url)] == response_url


def test_create_duplicate_awaiting_instances(valid_user_client, valid_user):
    workbasket = factories.WorkBasketFactory.create(
        status=WorkflowStatus.EDITING,
    )
    with workbasket.new_transaction() as transaction:
        TransactionCheckFactory.create(
            transaction=transaction,
            successful=True,
            completed=True,
        )

    session = valid_user_client.session
    session["workbasket"] = {
        "id": workbasket.pk,
        "status": workbasket.status,
        "title": workbasket.title,
        "error_count": workbasket.tracked_model_check_errors.count(),
    }
    session.save()

    workbasket.submit_for_approval()
    workbasket.save()
    workbasket.approve(valid_user.pk, settings.TRANSACTION_SCHEMA)
    workbasket.save()
    existing_packaged = factories.PackagedWorkBasketFactory.create(
        workbasket=workbasket,
    )

    workbasket.unapprove()
    workbasket.save()

    """Test that a WorkBasket cannot enter the packaging queue more than
    once."""
    create_url = reverse("publishing:packaged-workbasket-queue-ui-create")

    form_data = {
        "theme": "My theme",
        "jira_url": "www.fakejiraticket.com",
    }

    response = valid_user_client.post(create_url, form_data)

    assert response.status_code == 302
    response_url = reverse("publishing:packaged-workbasket-queue-ui-list")
    # Only compare the response URL up to the query string.
    assert response.url == response_url
