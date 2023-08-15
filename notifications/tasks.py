import logging

from celery import shared_task
from django.db.transaction import atomic

logger = logging.getLogger(__name__)


@shared_task
@atomic
def send_emails(notification_id: int):
    """Task for emailing all users signed up to receive packaging updates and
    creating a log to record which users received which email template."""
    from notifications.models import Notification

    notification = Notification.objects.get(id=notification_id)
    notification.send()
