from django.db.models import FileField
from django.db.models import QuerySet
from django.db.models import TextField

from common.models.mixins import TimestampedMixin
from publishing.models.state import ProcessingState
from publishing.storages import LoadingReportStorage


class LoadingReportQuerySet(QuerySet):
    def accepted(self):
        """Filter in those instances that were accepted by HMRC - that is, their
        related `PackagedWorkBasket` instance has a `processing_state` attribute
        value of SUCCESSFULLY_PROCESSED."""
        return self.filter(
            packagedworkbasket__processing_state=ProcessingState.SUCCESSFULLY_PROCESSED,
        )

    def rejected(self):
        """Filter in those instances that were rejected by HMRC - that is, their
        related `PackagedWorkBasket` instance has a `processing_state` attribute
        value of FAILED_PROCESSING."""
        return self.filter(
            packagedworkbasket__processing_state=ProcessingState.FAILED_PROCESSING,
        )


class LoadingReport(TimestampedMixin):
    """Report associated with an attempt to load (process) a PackagedWorkBasket
    instance."""

    objects = LoadingReportQuerySet.as_manager()

    file = FileField(
        blank=True,
        null=True,
        storage=LoadingReportStorage,
    )
    comments = TextField(
        blank=True,
        max_length=200,
    )
