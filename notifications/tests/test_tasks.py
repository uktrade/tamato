from unittest.mock import patch

import factory
import pytest

from notifications import models
from notifications import tasks

pytestmark = pytest.mark.django_db


def test_send_emails_goods_report_notification(
    goods_report_notification,
):
    """Tests that email notifications are only sent to users subscribed to email
    type and that a log is created with this user's email."""
    expected_present_email = "goods_report@email.co.uk"  # /PS-IGNORE
    expected_unenrolled_email = "no_goods_report@email.co.uk"  # /PS-IGNORE

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
        with patch(
            "notifications.models.send_emails",
            return_value={
                "response_ids": " \n".join([str(factory.Faker("uuid"))]),
                "recipients": " \n".join([expected_present_email]),
                "failed_recipients": "",
            },
        ) as mocked_send_emails:
            tasks.send_emails_task.apply(
                kwargs={
                    "notification_pk": goods_report_notification.id,
                },
            )
            mocked_send_emails.assert_called_once()
            mocked_prepare_link_to_file.assert_called_once()

    log = models.NotificationLog.objects.get(
        notification=goods_report_notification,
        recipients=expected_present_email,
        success=True,
    )

    assert expected_unenrolled_email not in log.recipients


def test_send_emails_packaging_notification(
    ready_for_packaging_notification,
):
    """Tests that email notifications are only sent to users subscribed to email
    type and that a log is created with this user's email."""

    expected_present_email = "packaging@email.co.uk"  # /PS-IGNORE
    expected_unenrolled_email = "no_packaging@email.co.uk"  # /PS-IGNORE

    with patch(
        "notifications.models.send_emails",
        return_value={
            "response_ids": " \n".join([str(factory.Faker("uuid"))]),
            "recipients": " \n".join([expected_present_email]),
            "failed_recipients": "",
        },
    ) as mocked_send_emails:
        tasks.send_emails_task.apply(
            kwargs={
                "notification_pk": ready_for_packaging_notification.id,
            },
        )
        mocked_send_emails.assert_called_once()

    log = models.NotificationLog.objects.get(
        notification=ready_for_packaging_notification,
        recipients=expected_present_email,
        success=True,
    )

    assert expected_unenrolled_email not in log.recipients


def test_send_emails_publishing_notification(
    successful_publishing_notification,
    # mock_notify_send_emails,
):
    """Tests that email notifications are only sent to users subscribed to email
    type and that a log is created with this user's email."""

    expected_present_email = "publishing@email.co.uk"  # /PS-IGNORE
    expected_unenrolled_email = "no_publishing@email.co.uk"  # /PS-IGNORE

    with patch(
        "notifications.models.send_emails",
        return_value={
            "response_ids": " \n".join([str(factory.Faker("uuid"))]),
            "recipients": " \n".join([expected_present_email]),
            "failed_recipients": "",
        },
    ) as mocked_send_emails:
        tasks.send_emails_task.apply(
            kwargs={
                "notification_pk": successful_publishing_notification.id,
            },
        )
        mocked_send_emails.assert_called_once()

    log = models.NotificationLog.objects.get(
        notification=successful_publishing_notification,
        recipients=expected_present_email,
        success=True,
    )

    assert expected_unenrolled_email not in log.recipients
