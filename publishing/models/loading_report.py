from django.db.models import FileField
from django.db.models import TextField

from common.models.mixins import TimestampedMixin
from publishing.storages import LoadingReportStorage


class LoadingReport(TimestampedMixin):
    """Report associated with an attempt to load (process) a PackagedWorkBasket
    instance."""

    file = FileField(
        blank=True,
        null=True,
        storage=LoadingReportStorage,
    )
    comments = TextField(
        blank=True,
        max_length=200,
    )
