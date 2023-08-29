import logging

from django.conf import settings
from django.db import models
from django.db.models.query_utils import Q
from notifications_python_client.notifications import NotificationsAPIClient
from polymorphic.models import PolymorphicModel

from common.models.mixins import TimestampedMixin

logger = logging.getLogger(__name__)


class NotifiedUser(models.Model):
    """A NotifiedUser stores a user email address and whether that user is
    signed up to receive packaging notifications."""

    email = models.EmailField()
    enrol_packaging = models.BooleanField(default=True)
    enrol_api_publishing = models.BooleanField(default=False)

    def __str__(self):
        return self.email


class NotificationLog(TimestampedMixin):
    """
    A NotificationLog records which Notification a group of users received.

    We create one each time a group of users receive an email.
    """

    recipients = models.TextField()
    """Comma separated email addresses, as a single string, of the recipients of
    the notification."""
    notification = models.ForeignKey(
        "notifications.Notification",
        default=None,
        null=True,
    )


class Notification(PolymorphicModel):
    """
    Base class to manage sending notifications.

    Subclasses specialise this class's behaviour for specific categories of
    notification.
    """

    notified_object_pk: int
    """The primary key of the."""

    notified_object_pk = models.IntegerField(
        default=None,
        null=True,
    )

    def notify_template_id(self) -> str:
        """
        GOV.UK Notify template ID specific to each Notification sub-class.

        Implement in concrete subclasses.
        """
        raise NotImplementedError

    def notified_users(self) -> models.QuerySet[NotifiedUser]:
        """
        Returns the queryset of NotifiedUsers for a specific notifications.

        Implement in concrete subclasses.
        """
        raise NotImplementedError

    def notified_object(self) -> models.Model:
        """
        Returns the object instance that is being notified on.

        Implement in concrete subclasses.
        """
        raise NotImplementedError

    def schedule_send_emails(self, countdown=1):
        """Schedule a call to send a notification email, run as an asynchronous
        background task."""

        send_emails.apply_sync(args=[self.pk], countdown=countdown)

    def send_emails(self):
        """Send the notification emails to users via GOV.UK Notify."""

        notified_users = self.notified_users()
        if not notified_users:
            logger.error(
                f"No notified users for {self.__class__.__name__} "
                f"with pk={self.pk}",
            )
            return

        notifications_client = NotificationsAPIClient(settings.NOTIFICATIONS_API_KEY)
        recipients = ""
        for user in notified_users:
            try:
                notifications_client.send_email_notification(
                    email_address=user.email,
                    template_id=self.notify_template_id(),
                    # TODO: get personalisation data.
                    personalisation={},
                )

                recipients += f"{user.email} \n"
            except:
                logger.error(
                    f"Failed to send email notification to {user.email}.",
                )

        NotificationLog.objects.create(
            recipients=recipients,
            notification=self,
        )


class EnvelopeReadyForProcessingNotification(Notification):
    """Manage sending notifications when envelopes are ready for processing by
    HMRC."""

    def notify_template_id(self) -> str:
        return settings.READY_FOR_CDS_TEMPLATE_ID

    def notified_users(self):
        return NotifiedUser.objects.filter(
            Q(enrol_packaging=True) | Q(enrole_api_publishing=True),
        )

    def notified_object(self) -> models.Model:
        from publishing.models import PackagedWorkBasket

        return (
            PackagedWorkBasket.objects.get(self.notified_object_pk)
            if self.notified_object_pk
            else None
        )


class EnvelopeAcceptedNotification(Notification):
    """TODO."""


class EnvelopeRejectedNotification(Notification):
    """TODO."""


class GoodsSuccessfulImportNotification(Notification):
    """TODO."""


# ========================== start ==========================
# Code between start and end is a rewrite of, and drop-in replacement for,
# notifications.tasks.send_emails().

from celery import shared_task
from django.db.transaction import atomic


@shared_task
@atomic
def send_emails(notification_pk: int):
    notification = Notification.objects.get(pk=notification_pk)
    notification.send_emails()


# ========================== end ==========================
