import logging

from django.db import models
from django.db.models import fields
from polymorphic.managers import PolymorphicManager

from checks.querysets import TrackedModelCheckQueryset
from common.models import TimestampedMixin
from common.models.celerytask import TaskModel
from common.models.trackedmodel import TrackedModel

logger = logging.getLogger(__name__)


class TrackedModelCheck(TimestampedMixin, TaskModel):
    """
    Represents the result of running a single check against a single model.

    Stores `content_hash`, a hash of the content for validity checking of the
    stored result.
    """

    class Meta:
        unique_together = ("model", "check_name")

    objects = PolymorphicManager.from_queryset(TrackedModelCheckQueryset)()
    model = models.ForeignKey(
        TrackedModel,
        related_name="checks",
        on_delete=models.SET_NULL,
        null=True,
    )

    check_name = fields.CharField(max_length=255)
    """A string identifying the type of check carried out."""

    successful = fields.BooleanField()
    """True if the check was successful."""

    message = fields.TextField(null=True)
    """The text content returned by the check, if any."""

    content_hash = models.BinaryField(max_length=32, null=True)
    """
    Hash of the content ('copyable_fields') at the time the data was checked.
    """

    def __str__(self):
        if self.successful:
            return f"{self.model} {self.check_name}  [Passed at {self.updated_at}]"

        return f"{self.model} {self.check_name} [Failed at {self.updated_at},  Message: {self.message}]"
