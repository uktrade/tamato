from unittest import mock

import pytest
from bs4 import BeautifulSoup
from django.conf import settings
from django.urls import reverse

from checks.tests.factories import TransactionCheckFactory
from common.tests import factories
from publishing.models import PackagedWorkBasket
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
    """Tests that Packaged WorkBasket Create returns 403 to user without
    publishing.add_packagedworkbasket permission."""
    create_url = reverse("publishing:packaged-workbasket-queue-ui-create")
    form_data = {
        "theme": "My theme",
        "jira_url": "www.fakejiraticket.com",
    }
    user = factories.UserFactory.create()
    client.force_login(user)
    response = client.post(create_url, form_data)

    assert response.status_code == 403


def test_packaged_workbasket_create_form_no_rule_check(
    valid_user_client,
    user_workbasket,
):
    """Tests that Packaged WorkBasket Create returns 302 and redirects work
    basket summary when no rule check has been executed."""
    create_url = reverse("publishing:packaged-workbasket-queue-ui-create")

    form_data = {
        "theme": "My theme",
        "jira_url": "www.fakejiraticket.com",
    }

    response = valid_user_client.post(create_url, form_data)

    assert (
        not PackagedWorkBasket.objects.all_queued()
        .filter(
            workbasket=user_workbasket,
        )
        .exists()
    )

    assert response.status_code == 302
    response_url = reverse("workbaskets:current-workbasket")
    # Only compare the response URL up to the query string.
    assert response.url[: len(response_url)] == response_url


def test_packaged_workbasket_create_form(client, valid_user, workbasket):
    """Tests that Packaged WorkBasket Create returns 302 and redirects to
    confirm create page on success."""
    client.force_login(valid_user)
    workbasket.set_as_current(valid_user)
    with workbasket.new_transaction() as transaction:
        TransactionCheckFactory.create(
            transaction=transaction,
            successful=True,
            completed=True,
        )

    # creating a packaged workbasket in the queue
    first_packaged_work_basket = factories.PackagedWorkBasketFactory()
    create_url = reverse("publishing:packaged-workbasket-queue-ui-create")

    form_data = {
        "theme": "My theme",
        "jira_url": "www.fakejiraticket.com",
    }

    response = client.post(create_url, form_data)

    assert response.status_code == 302
    assert "/confirm-create/" in response.url
    #  get the packaged workbasket we have made from the queued, filtering it by workbasket
    second_packaged_work_basket = (
        PackagedWorkBasket.objects.all_queued()
        .filter(
            workbasket=workbasket.pk,
        )
        .get()
    )

    response_url = f"/publishing/{second_packaged_work_basket.id}/confirm-create/"
    # Only compare the response URL up to the query string.
    assert response.url[: len(response_url)] == response_url
    assert second_packaged_work_basket.theme == form_data["theme"]
    # Check in, form field may not contain full URL contained within URLField object
    assert form_data["jira_url"] in second_packaged_work_basket.jira_url
    assert first_packaged_work_basket.position > 0
    assert first_packaged_work_basket.position < second_packaged_work_basket.position


def test_packaged_workbasket_create_form_rule_check_violations(client, valid_user):
    """Tests that Packaged WorkBasket Create returns 302 and redirects to
    workbasket detail page when there are rule check violations on
    workbasket."""
    client.force_login(valid_user)
    workbasket = factories.WorkBasketFactory.create(
        status=WorkflowStatus.EDITING,
    )
    workbasket.set_as_current(valid_user)
    with workbasket.new_transaction() as transaction:
        TransactionCheckFactory.create(
            transaction=transaction,
            successful=False,
            completed=True,
        )

    create_url = reverse("publishing:packaged-workbasket-queue-ui-create")

    form_data = {
        "theme": "My theme",
        "jira_url": "www.fakejiraticket.com",
    }

    response = client.post(create_url, form_data)
    #  assert the packaged workbasket does not exist
    assert (
        not PackagedWorkBasket.objects.all_queued()
        .filter(
            workbasket=workbasket,
        )
        .exists()
    )

    assert response.status_code == 302
    response_url = reverse("workbaskets:current-workbasket")
    # Only compare the response URL up to the query string.
    assert response.url[: len(response_url)] == response_url


def test_create_duplicate_awaiting_instances(client, valid_user, workbasket):
    """Tests that Packaged WorkBasket Create returns 302 and redirects to
    packaged workbasket queue page when trying to package a workbasket that is
    already on the queue."""
    client.force_login(valid_user)
    workbasket.set_as_current(valid_user)
    with workbasket.new_transaction() as transaction:
        TransactionCheckFactory.create(
            transaction=transaction,
            successful=True,
            completed=True,
        )

    workbasket.queue(valid_user.pk, settings.TRANSACTION_SCHEMA)
    workbasket.save()
    existing_packaged = factories.PackagedWorkBasketFactory.create(
        workbasket=workbasket,
    )

    workbasket.dequeue()
    workbasket.save()
    """Test that a WorkBasket cannot enter the packaging queue more than
    once."""
    create_url = reverse("publishing:packaged-workbasket-queue-ui-create")

    form_data = {
        "theme": "My theme",
        "jira_url": "www.fakejiraticket.com",
    }

    response = client.post(create_url, form_data)

    assert response.status_code == 302
    response_url = reverse("publishing:packaged-workbasket-queue-ui-list")
    # Only compare the response URL up to the query string.
    assert response.url == response_url


@mock.patch(
    "publishing.models.envelope.Envelope.xml_file_exists",
    return_value=True,
)
def test_find_processed_envelopes_list_view(
    mock_xml_file_exists,
    valid_user_client,
    successful_envelope_factory,
):
    settings.ENABLE_PACKAGING_NOTIFICATIONS = False

    envelope = successful_envelope_factory()

    response = valid_user_client.get(
        reverse("publishing:envelope-list-ui-list"),
    )
    assert response.status_code == 200

    page = BeautifulSoup(str(response.content), "html.parser")
    assert "Find processed envelopes" in page.select("h1")[0].text
    envelope_row = page.select("table.envelopes tbody tr")[0]
    assert envelope.envelope_id in envelope_row.select("td")[0].text


from publishing.models.envelope import EnvelopeQuerySet


@mock.patch(
    "publishing.models.envelope.Envelope.get_versions",
    return_value=mock.MagicMock(spec=EnvelopeQuerySet),
)
@mock.patch(
    "publishing.models.envelope.Envelope.xml_file_exists",
    return_value=True,
)
def test_envelope_history_for_view(
    mock_xml_file_exists,
    mock_get_versions,
    valid_user_client,
    successful_envelope_factory,
):
    settings.ENABLE_PACKAGING_NOTIFICATIONS = False

    envelope = successful_envelope_factory()

    mock_get_versions.filter.return_value = mock_get_versions
    mock_get_versions.all.return_value = [envelope]

    response = valid_user_client.get(
        reverse(
            "publishing:envelope-history-ui-detail",
            kwargs={"envelope_id": f"{envelope.envelope_id}"},
        ),
    )
    assert response.status_code == 200

    page = BeautifulSoup(str(response.content), "html.parser")
    assert f"Envelope history for {envelope.xml_file_name}" in page.select("h1")[0].text
