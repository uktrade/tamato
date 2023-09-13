import pytest

from notifications import models
from notifications import tasks

pytestmark = pytest.mark.django_db


def test_send_emails_goods_report_notification(
    goods_report_notification,
    mock_notify_send_emails,
):
    """Tests that email notifications are only sent to users subscribed to email
    type and that a log is created with this user's email."""
    expected_present_email = "goods_report@email.co.uk"  # /PS-IGNORE
    expected_unenrolled_email = "no_goods_report@email.co.uk"  # /PS-IGNORE

    tasks.send_emails_task.apply(
        kwargs={
            "notification_pk": goods_report_notification.id,
        },
    )

    recipients = f"{expected_present_email} \n"

    log = models.NotificationLog.objects.get(
        notification=goods_report_notification,
        recipients=recipients,
        success=True,
    )

    assert expected_unenrolled_email not in log.recipients


def test_send_emails_packaging_notification(
    ready_for_packaging_notification,
    mock_notify_send_emails,
):
    """Tests that email notifications are only sent to users subscribed to email
    type and that a log is created with this user's email."""

    expected_present_email = "packaging@email.co.uk"  # /PS-IGNORE
    expected_unenrolled_email = "no_packaging@email.co.uk"  # /PS-IGNORE

    tasks.send_emails_task.apply(
        kwargs={
            "notification_pk": ready_for_packaging_notification.id,
        },
    )
    recipients = f"{expected_present_email} \n"

    log = models.NotificationLog.objects.get(
        notification=ready_for_packaging_notification,
        recipients=recipients,
        success=True,
    )

    assert expected_unenrolled_email not in log.recipients


def test_send_emails_publishing_notification(
    successful_publishing_notification,
    mock_notify_send_emails,
):
    """Tests that email notifications are only sent to users subscribed to email
    type and that a log is created with this user's email."""

    expected_present_email = "publishing@email.co.uk"  # /PS-IGNORE
    expected_unenrolled_email = "no_publishing@email.co.uk"  # /PS-IGNORE

    tasks.send_emails_task.apply(
        kwargs={
            "notification_pk": successful_publishing_notification.id,
        },
    )

    recipients = f"{expected_present_email} \n"

    log = models.NotificationLog.objects.get(
        notification=successful_publishing_notification,
        recipients=recipients,
        success=True,
    )

    assert expected_unenrolled_email not in log.recipients
