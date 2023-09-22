import logging

from celery import shared_task
from django.conf import settings
from django.db.transaction import atomic

logger = logging.getLogger(__name__)


@shared_task(
    default_retry_delay=settings.NOTIFICATIONS_DEFAULT_RETRY_DELAY,
    max_retries=settings.NOTIFICATIONS_MAX_RETRIES,
    retry_backoff=True,
    retry_backoff_max=settings.NOTIFICATIONS_RETRY_BACKOFF_MAX,
    retry_jitter=True,
    autoretry_for=(Exception,),
)
@atomic
def send_emails_task(notification_pk: int):
    """Task for emailing all users signed up to receive packaging updates and
    creating a log to record which users received which email template."""
    from notifications.models import Notification

    notification = Notification.objects.get(pk=notification_pk)
    sub_notification = notification.return_subclass_instance()
    sub_notification.send_notification_emails()
