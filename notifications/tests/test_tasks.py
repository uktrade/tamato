from unittest.mock import patch
from uuid import uuid4

import pytest

from common.tests import factories
from notifications import models
from notifications import tasks

pytestmark = pytest.mark.django_db


@pytest.mark.skip(reason="TODO mock Notify client correctly")
@patch("notifications.tasks.NotificationsAPIClient.send_email_notification")
def test_send_emails_cds(send_email_notification, settings):
    """Tests that email notifications are only sent to users subscribed to
    packaging emails and that a log is created with this user's email and
    template id."""
    enrolled_user = factories.NotifiedUserFactory.create()
    unenrolled_user = factories.NotifiedUserFactory.create(enrol_packaging=False)
    template_id = uuid4()

    personalisation = {
        "envelope_id": "220001",
        "description": "description",
        "download_url": "https://example.com",
        "theme": "theme",
        "eif": None,
        "embargo": "None",
        "jira_url": "https://example.com",
    }

    tasks.send_emails.apply(
        kwargs={
            "template_id": template_id,
            "personalisation": personalisation,
            "email_type": "packaging",
        },
    )

    send_email_notification.assert_called_once_with(
        email_address=enrolled_user.email,
        template_id=template_id,
        personalisation=personalisation,
    )

    recipients = f"{enrolled_user.email} \n"
    log = models.NotificationLog.objects.get(
        template_id=template_id,
        recipients=recipients,
    )

    assert unenrolled_user.email not in log.recipients


@pytest.mark.skip(reason="TODO mock Notify client correctly")
@patch("notifications.tasks.NotificationsAPIClient.send_email_notification")
def test_send_emails_api(send_email_notification, settings):
    """Tests that email notifications are only sent to users subscribed to
    packaging emails and that a log is created with this user's email and
    template id."""
    enrolled_user = factories.NotifiedUserFactory.create(
        enrol_packaging=False,
        enrol_api_publishing=True,
    )
    unenrolled_user = factories.NotifiedUserFactory.create(enrol_packaging=False)
    template_id = uuid4()

    personalisation = {
        "envelope_id": "220001",
    }

    tasks.send_emails.apply(
        kwargs={
            "template_id": template_id,
            "personalisation": personalisation,
            "email_type": "publishing",
        },
    )

    send_email_notification.assert_called_once_with(
        email_address=enrolled_user.email,
        template_id=template_id,
        personalisation=personalisation,
    )

    recipients = f"{enrolled_user.email} \n"
    log = models.NotificationLog.objects.get(
        template_id=template_id,
        recipients=recipients,
    )

    assert unenrolled_user.email not in log.recipients
