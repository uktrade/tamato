import logging

from django.conf import settings
from django.db import models
from django.db.models.query_utils import Q
from django.urls import reverse

from common.models.mixins import TimestampedMixin
from notifications.notify import prepare_link_to_file
from notifications.notify import send_emails
from notifications.tasks import send_emails_task

logger = logging.getLogger(__name__)


class NotifiedUser(models.Model):
    """A NotifiedUser stores a user email address and whether that user is
    signed up to receive packaging notifications."""

    email = models.EmailField()
    enrol_packaging = models.BooleanField(default=True)
    enrol_api_publishing = models.BooleanField(default=False)
    enrol_goods_report = models.BooleanField(default=False)

    def __str__(self) -> str:
        return str(self.email)


class NotificationLog(TimestampedMixin):
    """
    A NotificationLog records which Notification a group of users received.

    We create one each time a group of users receive an email.
    """

    response_ids = models.TextField(
        default=None,
        null=True,
    )
    recipients = models.TextField()
    """Comma separated email addresses, as a single string, of the recipients of
    the notification."""
    notification = models.ForeignKey(
        "notifications.Notification",
        default=None,
        null=True,
        on_delete=models.PROTECT,
    )
    success = models.BooleanField(default=True)


# class NotificationManager(models.Manager):


class NotificationTypeChoices(models.TextChoices):
    GOODS_REPORT = (
        "goods_report",
        "Goods Report",
    )
    PACKAGING_NOTIFY_READY = (
        "packaging_notify_ready",
        "Packaging Notify Ready",
    )
    PACKAGING_ACCEPTED = (
        "packaging_accepted",
        "Packaging Accepted",
    )
    PACKAGING_REJECTED = (
        "packaging_rejected",
        "Packaging Rejected",
    )
    PUBLISHING_SUCCESS = (
        "publishing_success",
        "Publishing Successful",
    )
    PUBLISHING_FAILED = (
        "publishing_failed",
        "Publishing Failed",
    )


class Notification(models.Model):
    """
    Base class to manage sending notifications.

    Subclasses specialise this class's behaviour for specific categories of
    notification.

    Subclasses should specify the proxy model of inheritance:
    https://docs.djangoproject.com/en/dev/topics/db/models/#proxy-models
    """

    # def __init__(self, notificaiton_type: NotificationTypeChoices, notified_object_pk: int = None,  ):
    #     self.notified_object_pk = notified_object_pk
    #     self.notificaiton_type = notificaiton_type

    notified_object_pk = models.IntegerField(
        default=None,
        null=True,
    )
    """The primary key of the object being notified on."""

    notification_type = models.CharField(
        max_length=100,
        choices=NotificationTypeChoices.choices,
    )

    def return_subclass_instance(self) -> "Notification":
        subclasses = {
            NotificationTypeChoices.GOODS_REPORT: GoodsSuccessfulImportNotification,
            NotificationTypeChoices.PACKAGING_ACCEPTED: EnvelopeAcceptedNotification,
            NotificationTypeChoices.PACKAGING_NOTIFY_READY: EnvelopeReadyForProcessingNotification,
            NotificationTypeChoices.PACKAGING_REJECTED: EnvelopeRejectedNotification,
            NotificationTypeChoices.PUBLISHING_SUCCESS: CrownDependenciesEnvelopeSuccessNotification,
            NotificationTypeChoices.PUBLISHING_FAILED: CrownDependenciesEnvelopeFailedNotification,
        }
        self.__class__ = subclasses[self.notification_type]
        return self

    def get_personalisation(self) -> dict:
        """
        Returns the personalisation of the notified object.

        Implement in concrete subclasses.
        """
        raise NotImplementedError

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

    def synchronous_send_emails(self):
        """Synchronously call to send a notification email."""
        send_emails_task(self.pk)

    def schedule_send_emails(self, countdown=1):
        """Schedule a call to send a notification email, run as an asynchronous
        background task."""
        send_emails_task.apply_async(args=[self.pk], countdown=countdown)

    def send_notification_emails(self):
        """Send the notification emails to users via GOV.UK Notify."""

        notified_users = self.notified_users()
        if not notified_users:
            logger.error(
                f"No notified users for {self.__class__.__name__} "
                f"with pk={self.pk}",
            )
            return

        personalisation = self.get_personalisation()

        result = send_emails(
            self.notify_template_id(),
            personalisation,
            [user.email for user in notified_users],
        )

        NotificationLog.objects.create(
            response_ids=result["response_ids"],
            recipients=result["recipients"],
            notification=self,
        )

        # if any emails failed create a log for unsuccessful emails
        if result["failed_recipients"]:
            NotificationLog.objects.create(
                recipients=result["failed_recipients"],
                notification=self,
                success=False,
            )


class EnvelopeReadyForProcessingNotification(Notification):
    """Manage sending notifications when envelopes are ready for processing by
    HMRC."""

    class Meta:
        proxy = True

    def __init__(self, notified_object_pk: int):
        super(EnvelopeReadyForProcessingNotification, self).__init__(
            notified_object_pk=notified_object_pk,
            notification_type=NotificationTypeChoices.PACKAGING_NOTIFY_READY,
        )

    def get_personalisation(self) -> dict:
        packaged_workbasket = self.notified_object()
        eif = "Immediately"
        if packaged_workbasket.eif:
            eif = packaged_workbasket.eif.strftime("%d/%m/%Y")

        personalisation = {
            "envelope_id": packaged_workbasket.envelope.envelope_id,
            "description": packaged_workbasket.description,
            "download_url": (
                settings.BASE_SERVICE_URL + reverse("publishing:envelope-queue-ui-list")
            ),
            "theme": packaged_workbasket.theme,
            "eif": eif,
            "embargo": packaged_workbasket.embargo
            if packaged_workbasket.embargo
            else "None",
            "jira_url": packaged_workbasket.jira_url,
        }
        return personalisation

    def notify_template_id(self) -> str:
        return settings.READY_FOR_CDS_TEMPLATE_ID

    def notified_users(self):
        return NotifiedUser.objects.filter(
            Q(enrol_packaging=True),
        )

    def notified_object(self) -> models.Model:
        from publishing.models import PackagedWorkBasket

        return (
            PackagedWorkBasket.objects.get(pk=self.notified_object_pk)
            if self.notified_object_pk
            else None
        )


class EnvelopeAcceptedNotification(Notification):
    """Manage sending notifications when envelopes have been accepted by
    HMRC."""

    class Meta:
        proxy = True

    def __init__(self, notified_object_pk: int):
        super(EnvelopeAcceptedNotification, self).__init__(
            notified_object_pk=notified_object_pk,
            notification_type=NotificationTypeChoices.PACKAGING_ACCEPTED,
        )

    def get_personalisation(self) -> dict:
        packaged_workbasket = self.notified_object()
        loading_report_message = "Loading report: No loading report was provided."
        loading_reports = packaged_workbasket.loadingreports.exclude(
            file_name="",
        ).values_list(
            "file_name",
            flat=True,
        )
        if loading_reports:
            file_names = ", ".join(loading_reports)
            loading_report_message = f"Loading report(s): {file_names}"

        personalisation = {
            "envelope_id": packaged_workbasket.envelope.envelope_id,
            "transaction_count": packaged_workbasket.workbasket.transactions.count(),
            "loading_report_message": loading_report_message,
            "comments": packaged_workbasket.loadingreports.first().comments,
        }
        return personalisation

    def notify_template_id(self) -> str:
        return settings.CDS_ACCEPTED_TEMPLATE_ID

    def notified_users(self):
        return NotifiedUser.objects.filter(
            Q(enrol_packaging=True),
        )

    def notified_object(self) -> models.Model:
        from publishing.models import PackagedWorkBasket

        return (
            PackagedWorkBasket.objects.get(self.notified_object_pk)
            if self.notified_object_pk
            else None
        )


class EnvelopeRejectedNotification(Notification):
    """Manage sending notifications when envelopes have been rejected by
    HMRC."""

    class Meta:
        proxy = True

    def __init__(self, notified_object_pk: int):
        super(EnvelopeRejectedNotification, self).__init__(
            notified_object_pk=notified_object_pk,
            notification_type=NotificationTypeChoices.PACKAGING_REJECTED,
        )

    def get_personalisation(self) -> dict:
        packaged_workbasket = self.notified_object()
        loading_report_message = "Loading report: No loading report was provided."
        loading_reports = packaged_workbasket.loadingreports.exclude(
            file_name="",
        ).values_list(
            "file_name",
            flat=True,
        )
        if loading_reports:
            file_names = ", ".join(loading_reports)
            loading_report_message = f"Loading report(s): {file_names}"

        personalisation = {
            "envelope_id": packaged_workbasket.envelope.envelope_id,
            "transaction_count": packaged_workbasket.workbasket.transactions.count(),
            "loading_report_message": loading_report_message,
            "comments": packaged_workbasket.loadingreports.first().comments,
        }
        return personalisation

    def notify_template_id(self) -> str:
        return settings.CDS_REJECTED_TEMPLATE_ID

    def notified_users(self):
        return NotifiedUser.objects.filter(
            Q(enrol_packaging=True),
        )

    def notified_object(self) -> models.Model:
        from publishing.models import PackagedWorkBasket

        return (
            PackagedWorkBasket.objects.get(pk=self.notified_object_pk)
            if self.notified_object_pk
            else None
        )


class CrownDependenciesEnvelopeSuccessNotification(Notification):
    """Manage sending notifications when envelopes have been successfully
    published to the Crown Dependencies api."""

    class Meta:
        proxy = True

    def __init__(self, notified_object_pk: int):
        super(CrownDependenciesEnvelopeSuccessNotification, self).__init__(
            notified_object_pk=notified_object_pk,
            notification_type=NotificationTypeChoices.PUBLISHING_SUCCESS,
        )

    def get_personalisation(self) -> dict:
        crown_dependicies_envelope = self.notified_object()
        personalisation = {
            "envelope_id": crown_dependicies_envelope.packagedworkbaskets.last().envelope.envelope_id,
        }
        return personalisation

    def notify_template_id(self) -> str:
        return settings.API_PUBLISH_SUCCESS_TEMPLATE_ID

    def notified_users(self):
        return NotifiedUser.objects.filter(
            Q(enrol_api_publishing=True),
        )

    def notified_object(self) -> models.Model:
        from publishing.models import CrownDependenciesEnvelope

        return (
            CrownDependenciesEnvelope.objects.get(pk=self.notified_object_pk)
            if self.notified_object_pk
            else None
        )


class CrownDependenciesEnvelopeFailedNotification(Notification):
    """Manage sending notifications when envelopes have been failed being
    published to the Crown Dependencies api."""

    class Meta:
        proxy = True

    def __init__(self, notified_object_pk: int):
        super(CrownDependenciesEnvelopeFailedNotification, self).__init__(
            notified_object_pk=notified_object_pk,
            notification_type=NotificationTypeChoices.PUBLISHING_FAILED,
        )

    def get_personalisation(self) -> dict:
        self.notified_object()
        personalisation = {
            "envelope_id": self.packagedworkbaskets.last().envelope.envelope_id,
        }
        return personalisation

    def notify_template_id(self) -> str:
        return settings.API_PUBLISH_FAILED_TEMPLATE_ID

    def notified_users(self):
        return NotifiedUser.objects.filter(
            Q(enrol_api_publishing=True),
        )

    def notified_object(self) -> models.Model:
        from publishing.models import CrownDependenciesEnvelope

        return (
            CrownDependenciesEnvelope.objects.get(pk=self.notified_object_pk)
            if self.notified_object_pk
            else None
        )


class GoodsSuccessfulImportNotification(Notification):
    """Manage sending notifications when a goods report has been reviewed and
    can be sent to Crown Dependencies."""

    class Meta:
        proxy = True

    def __init__(self, notified_object_pk: int):
        super(GoodsSuccessfulImportNotification, self).__init__(
            notified_object_pk=notified_object_pk,
            notification_type=NotificationTypeChoices.GOODS_REPORT,
        )

    def get_personalisation(self) -> dict:
        import_batch = self.notified_object()
        personalisation = {
            "tgb_id": import_batch.name,
            "link_to_file": prepare_link_to_file(
                import_batch.taric_file,
                confirm_email_before_download=True,
            ),
        }
        return personalisation

    def notify_template_id(self) -> str:
        return settings.GOODS_REPORT_TEMPLATE_ID

    def notified_users(self):
        return NotifiedUser.objects.filter(
            Q(enrol_goods_report=True),
        )

    def notified_object(self) -> models.Model:
        from importer.models import ImportBatch

        return (
            ImportBatch.objects.get(id=self.notified_object_pk)
            if self.notified_object_pk
            else None
        )
