from unittest.mock import patch

import factory
import pytest

from importer.models import ImportBatch
from notifications.models import NotificationLog
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

    return_value = {
        "file": "VGVzdA==",
        "is_csv": False,
        "confirm_email_before_download": True,
        "retention_period": None,
    }
    with patch(
        "notifications.models.prepare_link_to_file",
        return_value=return_value,
    ) as mocked_prepare_link_to_file:
        personalisation = goods_report_notification.get_personalisation()

        assert personalisation == {
            "tgb_id": "0",
            "link_to_file": return_value,
        }


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
def test_send_notification_emails(ready_for_packaging_notification):
    expected_present_email = f"packaging@email.co.uk"  # /PS-IGNORE
    expected_not_present_email = f"no_packaging@email.co.uk"  # /PS-IGNORE
    with patch(
        "notifications.models.send_emails",
        return_value={
            "response_ids": " \n".join([str(factory.Faker("uuid"))]),
            "recipients": " \n".join([expected_present_email]),
            "failed_recipients": "",
        },
    ) as mocked_send_emails:
        ready_for_packaging_notification.send_notification_emails()
        mocked_send_emails.assert_called_once()

    log_success = NotificationLog.objects.get(
        notification=ready_for_packaging_notification,
        recipients=expected_present_email,
        success=True,
    )

    assert expected_present_email in log_success.recipients

    with patch(
        "notifications.models.send_emails",
        return_value={
            "response_ids": "",
            "recipients": "",
            "failed_recipients": " \n".join([expected_present_email]),
        },
    ) as mocked_send_emails:
        ready_for_packaging_notification.send_notification_emails()
        mocked_send_emails.assert_called_once()

    log_fail = NotificationLog.objects.get(
        notification=ready_for_packaging_notification,
        success=False,
    )

    assert expected_present_email in log_fail.recipients
