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
    (
        notification,
        expected_present_email,
        expected_not_present_email,
    ) = goods_report_notification

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
                    "notification_pk": notification.id,
                },
            )
            mocked_send_emails.assert_called_once()
            mocked_prepare_link_to_file.assert_called_once()

    log = models.NotificationLog.objects.get(
        notification=notification,
        recipients=expected_present_email,
        success=True,
    )

    assert expected_present_email in log.recipients
    assert expected_not_present_email not in log.recipients


def test_send_emails_packaging_notification(
    ready_for_packaging_notification,
):
    """Tests that email notifications are only sent to users subscribed to email
    type and that a log is created with this user's email."""

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
        tasks.send_emails_task.apply(
            kwargs={
                "notification_pk": notification.id,
            },
        )
        mocked_send_emails.assert_called_once()

    log = models.NotificationLog.objects.get(
        notification=notification,
        recipients=expected_present_email,
        success=True,
    )

    assert expected_present_email in log.recipients
    assert expected_not_present_email not in log.recipients


def test_send_emails_publishing_notification(
    successful_publishing_notification,
    # mock_notify_send_emails,
):
    """Tests that email notifications are only sent to users subscribed to email
    type and that a log is created with this user's email."""

    (
        notification,
        expected_present_email,
        expected_not_present_email,
    ) = successful_publishing_notification

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
                "notification_pk": notification.id,
            },
        )
        mocked_send_emails.assert_called_once()

    log = models.NotificationLog.objects.get(
        notification=notification,
        recipients=expected_present_email,
        success=True,
    )

    assert expected_present_email in log.recipients
    assert expected_not_present_email not in log.recipients
