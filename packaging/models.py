from django.db import models
from ordered_model.models import OrderedModel

from workbaskets.models import WorkBasket


class PackagingStateChoices(models.TextChoices):
    AWAITING_PROCESSING = "AP", "Awaiting processing"
    CURRENTLY_PROCESSING = "CP", "Currently processing"
    SUCCESSFULLY_PROCESSED = "SP", "Successfully processed"
    FAILED_PROCESSING = "FP", "Failed processing"


COMPLETED_PACKAGING_STATES = (
    PackagingStateChoices.SUCCESSFULLY_PROCESSED,
    PackagingStateChoices.FAILED_PROCESSING,
)


class Envelope(models.Model):
    envelope_id = models.CharField(
        max_length=10,
    )
    xml_file = models.FileField(
        null=True,
    )
    cds_report_file = models.FileField(
        null=True,
    )


class PackagedWorkBasket(OrderedModel):
    workbasket = models.ForeignKey(
        WorkBasket,
        on_delete=models.PROTECT,
        editable=False,
    )
    state = models.CharField(
        max_length=2,
        choices=PackagingStateChoices.choices,
        default=PackagingStateChoices.AWAITING_PROCESSING,
    )
    envelope = models.OneToOneField(
        Envelope,
        null=True,
        on_delete=models.PROTECT,
    )

    @property
    def has_completed_processing(self):
        return self.state in (
            PackagingStateChoices.SUCCESSFULLY_PROCESSED,
            PackagingStateChoices.FAILED_PROCESSING,
        )
