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

    (
        notification,
        expected_present_email,
        expected_not_present_email,
    ) = goods_report_notification

    users = notification.notified_users()

    for user in users:
        assert user.email == expected_present_email
        assert user.email != expected_not_present_email

    import_batch = notification.notified_object()
    assert isinstance(import_batch, ImportBatch)

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
        personalisation = notification.get_personalisation()

        assert personalisation == {
            "tgb_id": import_batch.name,
            "link_to_file": return_value,
        }


def test_create_packaging_notification(ready_for_packaging_notification):
    """Test that the creating a notification correctly assigns users."""

    (
        notification,
        expected_present_email,
        expected_not_present_email,
    ) = ready_for_packaging_notification

    users = notification.notified_users()

    for user in users:
        assert user.email == expected_present_email
        assert user.email != expected_not_present_email

    assert isinstance(
        notification.notified_object(),
        PackagedWorkBasket,
    )

    content = notification.get_personalisation()
    assert content == {
        "envelope_id": "230001",
        "description": "",
        "download_url": "http://localhost/publishing/envelope-queue/",
        "theme": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        "eif": "Immediately",
        "embargo": "None",
        "jira_url": "www.fakejiraticket.com",
    }


def test_create_accepted_envelope(accepted_packaging_notification):
    """Test that the creating a notification correctly assigns users."""

    (
        notification,
        expected_present_email,
        expected_not_present_email,
    ) = accepted_packaging_notification
    expected_present_email = f"packaging@email.co.uk"  # /PS-IGNORE
    expected_not_present_email = f"no_packaging@email.co.uk"  # /PS-IGNORE

    users = notification.notified_users()

    for user in users:
        assert user.email == expected_present_email
        assert user.email != expected_not_present_email

    assert isinstance(
        notification.notified_object(),
        PackagedWorkBasket,
    )

    content = notification.get_personalisation()
    assert "envelope_id" in content and content["envelope_id"] == "230001"
    assert "transaction_count" in content and content["transaction_count"] == 1
    assert (
        "loading_report_message" in content
        and content["loading_report_message"]
        == "Loading report(s): REPORT_DBT23000.html"
    )
    assert "comments" in content


def test_create_rejected_envelope(rejected_packaging_notification):
    """Test that the creating a notification correctly assigns users."""

    (
        notification,
        expected_present_email,
        expected_not_present_email,
    ) = rejected_packaging_notification
    expected_present_email = f"packaging@email.co.uk"  # /PS-IGNORE
    expected_not_present_email = f"no_packaging@email.co.uk"  # /PS-IGNORE

    users = notification.notified_users()

    for user in users:
        assert user.email == expected_present_email
        assert user.email != expected_not_present_email

    assert isinstance(
        notification.notified_object(),
        PackagedWorkBasket,
    )

    content = notification.get_personalisation()
    assert "envelope_id" in content and content["envelope_id"] == "230001"
    assert "transaction_count" in content and content["transaction_count"] == 1
    assert (
        "loading_report_message" in content
        and content["loading_report_message"]
        == "Loading report(s): REPORT_DBT23001.html"
    )
    assert "comments" in content


def test_create_successful_publishing_notification(successful_publishing_notification):
    """Test that the creating a notification correctly assigns users."""

    (
        notification,
        expected_present_email,
        expected_not_present_email,
    ) = successful_publishing_notification
    expected_present_email = f"publishing@email.co.uk"  # /PS-IGNORE
    expected_not_present_email = f"no_publishing@email.co.uk"  # /PS-IGNORE

    users = notification.notified_users()

    for user in users:
        assert user.email == expected_present_email
        assert user.email != expected_not_present_email

    assert isinstance(
        notification.notified_object(),
        CrownDependenciesEnvelope,
    )

    content = notification.get_personalisation()
    assert content == {"envelope_id": "230001"}


def test_create_failed_publishing_notification(failed_publishing_notification):
    """Test that the creating a notification correctly assigns users."""

    (
        notification,
        expected_present_email,
        expected_not_present_email,
    ) = failed_publishing_notification
    expected_present_email = f"publishing@email.co.uk"  # /PS-IGNORE
    expected_not_present_email = f"no_publishing@email.co.uk"  # /PS-IGNORE

    users = notification.notified_users()

    for user in users:
        assert user.email == expected_present_email
        assert user.email != expected_not_present_email

    assert isinstance(
        notification.notified_object(),
        CrownDependenciesEnvelope,
    )

    content = notification.get_personalisation()
    assert content == {"envelope_id": "230001"}


def test_send_notification_emails(ready_for_packaging_notification):
    (
        notification,
        expected_present_email,
        expected_not_present_email,
    ) = ready_for_packaging_notification

    with patch(
        "notifications.models.send_emails",
        return_value={
            "response_ids": " \n".join([str(factory.Faker("uuid"))]),
            "recipients": " \n".join([expected_present_email]),
            "failed_recipients": "",
        },
    ) as mocked_send_emails:
        notification.send_notification_emails()
        mocked_send_emails.assert_called_once()

    log_success = NotificationLog.objects.get(
        notification=notification,
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
        notification.send_notification_emails()
        mocked_send_emails.assert_called_once()

    log_fail = NotificationLog.objects.get(
        notification=notification,
        success=False,
    )

    assert expected_present_email in log_fail.recipients
