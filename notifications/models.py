import logging
from tempfile import NamedTemporaryFile
from uuid import uuid4

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.transaction import atomic

from common.models.mixins import TimestampedMixin
from importer.goods_report import GoodsReporter
from notifications.notification_type import GOODS_REPORT
from notifications.notification_type import NOTIFICATION_CHOICES
from notifications.notification_type import NotificationType
from notifications.notifications_api import get_notificaiton_api_interface

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
    A NotificationLog records which email template a group of users received.

    We create one each time a group of users receive an email.
    """

    template_id = models.CharField(max_length=100)
    response_id: uuid4 = models.CharField(
        max_length=100,
        null=True,
    )
    recipients = models.TextField()
    notification: "Notification" = models.ForeignKey(
        "Notification",
        on_delete=models.PROTECT,
        editable=False,
        null=True,
    )
    success = models.BooleanField(default=True)


# class NotificationType(models.TextChoices):

#     GOODS_REPORT = ("goods_report", "Goods Report", models.Q(enrol_goods_report=True))
#     PACKAGING = ("packaging", "Packaging", models.Q(enrol_packaging=True))
#     PUBLISHING = ("publishing", "Publishing",  models.Q(enrol_api_publishing=True))

#     def __new__(cls, value, query):
#         obj = str.__new__(cls, value)
#         obj._value_ = value
#         obj.query = query
#         return obj


class NotificationManager(models.Manager):
    @atomic
    def create(
        self,
        template_id: str,
        email_type: NotificationType,
        attachment_object: GenericForeignKey = None,
        personalisation: dict = {},
        **kwargs,
    ) -> "Notification":
        """
        Create a new notifiacation instance, uses the email type to retrieve all
        the enroled users. If email type has associated attachments attach the
        object to the model. Currently attaches an ImportBatch if it's a goods
        report email.

        :param template_id: notification tempalte to use
        :param email_type: which type of email is being sent
        :param attachment_id: optional attachment id for the object to send as an attachment
        :param personalisation: personalised data to display in the email
        """
        users = NotifiedUser.objects.filter(email_type.query)
        notification = super().create(
            template_id=template_id,
            personalisation=personalisation,
            attachment_object=attachment_object,
            **kwargs,
        )

        notification.notified_users.add(*users)

        notification.save()

        return notification


class NotificationQuerySet(models.QuerySet):
    # TODO add queryset's for email type
    def none(self) -> "NotificationQuerySet":
        return None


class Notification(TimestampedMixin):
    """
    Represents a Notification.

    This model contains the users to notify, the object to attach, the template
    id and personalistation for the email.

    Has the property client which stores the Notification client the email is
    using.

    Contains a send function which generates the attachment if required and send
    the email via the client. It then records the result in the NotificationLog
    model.
    """

    email_type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_CHOICES,
    )

    notified_users = models.ManyToManyField(NotifiedUser)
    attachment_id = models.PositiveIntegerField(null=True)
    attachment_type = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
        null=True,
    )
    attachment_object = GenericForeignKey(
        ct_field="attachment_type",
        fk_field="attachment_id",
    )
    template_id: uuid4 = models.CharField(max_length=100)
    personalisation: dict = models.JSONField()

    @property
    def client(self):
        return get_notificaiton_api_interface()

    class Meta:
        ordering = ("pk",)

    objects: NotificationQuerySet = NotificationManager.from_queryset(
        NotificationQuerySet,
    )()

    def send(self):
        if self.attachment_object:
            # if file attachment then the object should have a generate_attachment function
            # attachment = self.attachment_object.generate_attachment()
            # self.personalisation["link_to_file"] = self.client.prepare_upload(
            #         attachment,
            #         retention_period="4 weeks",
            #     )
            
            with NamedTemporaryFile(suffix=".xlsx") as tmp:
                reporter = GoodsReporter(self.attachment_object.taric_file)
                goods_report = reporter.create_report()
                goods_report.xlsx_file(tmp)
                self.personalisation["link_to_file"] = self.client.prepare_upload(
                    tmp,
                    retention_period="4 weeks",
                )
                self.save()

        if self.notified_users:
            recipients = ""
            for user in self.notified_users.all():
                try:
                    response = self.client.send_email(
                        email_address=user.email,
                        template_id=self.template_id,
                        personalisation=self.personalisation,
                    )
                    recipients += f"{user.email} \n"
                    NotificationLog.objects.create(
                        response_id=response["id"],
                        recipients=recipients,
                        notification=self,
                    )
                except Exception as e:
                    print(type(e))
                    logger.error(
                        f"Failed to send email notification to {user.email}.",
                    )
                    NotificationLog.objects.create(
                        recipients=recipients,
                        notification=self,
                        success=False,
                    )

    def __repr__(self) -> str:
        return f'<Notificataion: id="{self.pk}", email_type={self.email_type}>'
