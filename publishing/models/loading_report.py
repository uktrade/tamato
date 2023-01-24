from django.db import models

from common.models.mixins import TimestampedMixin
from publishing.storages import LoadingReportStorage


class LoadingReport(TimestampedMixin):
    """Report associated with an attempt to load (process) a PackagedWorkBasket
    instance."""

    file = models.FileField(
        blank=True,
        null=True,
        storage=LoadingReportStorage,
    )
    comments = models.TextField(
        blank=True,
        max_length=200,
    )
