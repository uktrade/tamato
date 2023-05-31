import logging
from uuid import uuid4

from celery import shared_task
from django.conf import settings
from django.db.models.query_utils import Q
from django.db.transaction import atomic
from notifications_python_client.notifications import NotificationsAPIClient

from notifications.models import NotificationLog
from notifications.models import NotifiedUser

logger = logging.getLogger(__name__)


def get_notifications_client():
    return NotificationsAPIClient(settings.NOTIFICATIONS_API_KEY)


@shared_task
@atomic
def send_emails(template_id: uuid4, personalisation: dict, email_type: str = None):
    """Task for emailing all users signed up to receive packaging updates and
    creating a log to record which users received which email template."""

    user_filters = {
        "packaging": Q(enrol_packaging=True),
        "publishing": Q(enrol_publishing=True),
    }
    # Will get all users by default
    users = NotifiedUser.objects.filter(user_filters.get(email_type, Q()))
    print(users)
    if users.exists():
        notifications_client = get_notifications_client()
        recipients = ""
        for user in users:
            try:
                notifications_client.send_email_notification(
                    email_address=user.email,
                    template_id=template_id,
                    personalisation=personalisation,
                )
                recipients += f"{user.email} \n"
            except:
                logger.error(
                    f"Failed to send email notification to {user.email}.",
                )

        NotificationLog.objects.create(
            template_id=template_id,
            recipients=recipients,
        )
