from django.db import models

from common.models.mixins import TimestampedMixin


class NotifiedUser(models.Model):
    """A NotifiedUser stores a user email address and whether that user is
    signed up to receive packaging notifications."""

    email = models.EmailField()
    enrol_packaging = models.BooleanField(default=True)

    def __str__(self):
        return self.email


class NotificationLog(TimestampedMixin):
    """
    A NotificationLog records which email template a group of users received.

    We create one each time a group of users receive an email.
    """

    template_id = models.CharField(max_length=100)
    recipients = models.TextField()
