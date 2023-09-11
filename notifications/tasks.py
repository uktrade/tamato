import logging

from celery import shared_task
from django.db.transaction import atomic

logger = logging.getLogger(__name__)


# def get_notifications_client():
#     return NotificationsAPIClient(settings.NOTIFICATIONS_API_KEY)
@shared_task
@atomic
def send_emails_task(notification_pk: int):
    """Task for emailing all users signed up to receive packaging updates and
    creating a log to record which users received which email template."""
    from notifications.models import Notification

    notification = Notification.objects.get(pk=notification_pk)
    sub_notification = notification.return_subclass_instance()
    sub_notification.send_emails()
