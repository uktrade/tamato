from uuid import uuid4

from celery import shared_task
from django.conf import settings
from django.db.transaction import atomic
from notifications_python_client.notifications import NotificationsAPIClient

from notifications.models import NotificationLog
from notifications.models import NotifiedUser


def get_notifications_client():
    return NotificationsAPIClient(settings.NOTIFICATIONS_API_KEY)


@shared_task
@atomic
def send_emails(template_id: uuid4, personalisation: dict):
    """Task for emailing all users signed up to receive packaging updates and
    creating a log to record which users received which email template."""
    users = NotifiedUser.objects.filter(enrol_packaging=True)

    if users.exists():
        notifications_client = get_notifications_client()
        recipients = ""
        for user in users:
            notifications_client.send_email_notification(
                email_address=user.email,
                template_id=template_id,
                personalisation=personalisation,
            )
            recipients += f"{user.email} \n"

        NotificationLog.objects.create(
            template_id=template_id,
            recipients=recipients,
        )
