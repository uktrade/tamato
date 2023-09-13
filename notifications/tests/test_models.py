import pytest

from importer.models import ImportBatch
from publishing.models import CrownDependenciesEnvelope
from publishing.models import PackagedWorkBasket

pytestmark = pytest.mark.django_db


def test_create_goods_report_notification(goods_report_notification):
    """Test that the creating a notification correctly assigns users."""

    expected_present_email = f"goods_report@email.co.uk"  # /PS-IGNORE
    expected_not_present_email = f"no_goods_report@email.co.uk"  # /PS-IGNORE

    users = goods_report_notification.notified_users()

    for user in users:
        assert user.email == expected_present_email
        assert user.email != expected_not_present_email

    assert isinstance(goods_report_notification.notified_object(), ImportBatch)
    # TODO check goods_report_notification.get_personalisation()


def test_create_packaging_notification(ready_for_packaging_notification):
    """Test that the creating a notification correctly assigns users."""

    expected_present_email = f"packaging@email.co.uk"  # /PS-IGNORE
    expected_not_present_email = f"no_packaging@email.co.uk"  # /PS-IGNORE

    users = ready_for_packaging_notification.notified_users()

    for user in users:
        assert user.email == expected_present_email
        assert user.email != expected_not_present_email

    assert isinstance(
        ready_for_packaging_notification.notified_object(),
        PackagedWorkBasket,
    )

    content = ready_for_packaging_notification.get_personalisation()
    assert content == {
        "envelope_id": "230001",
        "description": "",
        "download_url": "http://localhost/publishing/envelope-queue/",
        "theme": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        "eif": "Immediately",
        "embargo": "None",
        "jira_url": "www.fakejiraticket.com",
    }


def test_create_successful_publishing_notification(successful_publishing_notification):
    """Test that the creating a notification correctly assigns users."""

    expected_present_email = f"publishing@email.co.uk"  # /PS-IGNORE
    expected_not_present_email = f"no_publishing@email.co.uk"  # /PS-IGNORE

    users = successful_publishing_notification.notified_users()

    for user in users:
        assert user.email == expected_present_email
        assert user.email != expected_not_present_email

    assert isinstance(
        successful_publishing_notification.notified_object(),
        CrownDependenciesEnvelope,
    )

    content = successful_publishing_notification.get_personalisation()
    assert content == {"envelope_id": "230001"}


# TODO add test send_emails
