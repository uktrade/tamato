import logging

from celery import shared_task
from django.db.transaction import atomic

logger = logging.getLogger(__name__)


# def get_notifications_client():
#     return NotificationsAPIClient(settings.NOTIFICATIONS_API_KEY)
@shared_task
@atomic
def send_emails_task(notification_pk: int, notification_type: "Notification"):
    """Task for emailing all users signed up to receive packaging updates and
    creating a log to record which users received which email template."""
    print(notification_type)
    notification = notification_type.objects.get(pk=notification_pk)
    notification.send_emails()
