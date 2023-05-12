import logging

from django.db.models import DateTimeField
from django.db.models import Manager
from django.db.models import Max
from django.db.models import Q
from django.db.models import QuerySet
from django.db.transaction import atomic
from django_fsm import FSMField

from common.models.mixins import TimestampedMixin
from publishing.models import ApiPublishingState
from publishing.models import Envelope
from publishing.models import PackagedWorkBasket
from publishing.models import ProcessingState

logger = logging.getLogger(__name__)


# Exceptions
class ApiEnvelopeUnexpectedEnvelopeSequence(Exception):
    pass


class ApiEnvelopeInvalidWorkBasketStatus(Exception):
    pass


class ApiEnvelopeAlreadyExists(Exception):
    pass


class TAPApiEnvelopeManager(Manager):
    @atomic
    def create(self, packaged_work_basket, **kwargs):
        """
        Create a new instance, from the packaged workbasket successfully
        processed.

         :param packaged_work_basket: packaged workbasket to publish.
        @throws ApiEnvelopeInvalidWorkBasketStatus if packaged workbasket isn't Successfully processed
        @throws ApiEnvelopeAlreadyExists if packaged workbasket already has a TAPApiEnvelope
        @throws ApiEnvelopeUnexpectedEnvelopeSequence if packaged workbasket isn't expected envelope id
        """
        if (
            packaged_work_basket.processing_state
            != ProcessingState.SUCCESSFULLY_PROCESSED
        ):
            raise ApiEnvelopeInvalidWorkBasketStatus(
                "Unable to create TAPApiEnvelope from PackagedWorkBasket instance "
                f"PackagedWorkBasket status not successful, {packaged_work_basket.processing_state} status.",
            )

        if TAPApiEnvelope.objects.filter(
            packagedworkbaskets__envelope__envelope_id=packaged_work_basket.envelope.envelope_id,
        ).exists():
            raise ApiEnvelopeAlreadyExists(
                "Unable to create TAPApiEnvelope from PackagedWorkBasket instance PackagedWorkBasket already has a TAPApiEnvelope",
            )

        previous_id = (
            PackagedWorkBasket.objects.select_related(
                "envelope",
                "tap_api_envelope",
            )
            .filter(
                Q(
                    envelope__id__isnull=False,
                    envelope__published_to_tariffs_api__isnull=False,
                )
                | Q(tap_api_envelope__id__isnull=False),
            )
            .aggregate(
                Max("envelope__envelope_id"),
            )["envelope__envelope_id__max"]
        )
        """Join PackagedWorkBasket with Envelope and TAPApiEnvelope model
        selecting objects Where an Envelope model exists and the
        published_to_tariffs_api field is not null Or Where a TAPApiEnvelope is
        not null Then select the max value for ther envelope_id field in the
        Envelope instance."""

        if packaged_work_basket.envelope.envelope_id[:4] == "0001":
            year = packaged_work_basket.envelope.envelope_id[2:]
            expected_previous_id = (
                Envelope.objects.for_year(year=year - 1).last().envelope_id
            )
        else:
            expected_previous_id = str(
                int(packaged_work_basket.envelope.envelope_id) - 1,
            )

        if (
            previous_id
            and packaged_work_basket.envelope.envelope_id != expected_previous_id
        ):
            raise ApiEnvelopeUnexpectedEnvelopeSequence(
                "Unable to create TAPApiEnvelope from PackagedWorkBasket instance "
                f"Envelope Id {packaged_work_basket.envelope.envelope_id} is not the next not expected envelope",
            )
        envelope = super().create(**kwargs)

        return envelope


class ApiEnvelopeQuerySet(QuerySet):
    def awaiting_publishing(self):
        return self.filter(
            publishing_state=ApiPublishingState.AWAITING_PUBLISHING,
        )

    def unpublished(self):
        return (
            self.failed_publishing_staging()
            | self.failed_publishing_production()
            | self.awaiting_publishing()
        )

    def currently_publishing(self):
        return self.filter(
            publishing_state=ApiPublishingState.CURRENTLY_PUBLISHING,
        )

    def published(self):
        return self.filter(
            publishing_state=ApiPublishingState.SUCCESSFULLY_PUBLISHED,
        )

    def failed_publishing_staging(self):
        return self.filter(
            publishing_state=ApiPublishingState.FAILED_PUBLISHING_STAGING,
        )

    def failed_publishing_production(self):
        return self.filter(
            publishing_state=ApiPublishingState.FAILED_PUBLISHING_PRODUCTION,
        )

    def failed_publishing(self):
        return self.failed_publishing_staging() | self.failed_publishing_production()


class TAPApiEnvelope(TimestampedMixin):
    """
    Represents an API packaged envelope.

    This model contains the Envelope upload status to the Channel islands API and it's publishing times.

    An Envelope contains one or more Transactions, listing changes to be applied
    to the tariff in the sequence defined by the transaction IDs. Contains
    xml_file which is a reference to the envelope stored on s3. This can be found in the Envelope model.
    """

    class Meta:
        ordering = ("pk",)

    objects: ApiEnvelopeQuerySet = TAPApiEnvelopeManager.from_queryset(
        ApiEnvelopeQuerySet,
    )()

    publishing_state = FSMField(
        default=ApiPublishingState.AWAITING_PUBLISHING,
        choices=ApiPublishingState.choices,
        db_index=True,
        protected=True,
        editable=False,
    )

    production_published = DateTimeField(
        null=True,
        blank=True,
        default=None,
    )
    staging_published = DateTimeField(
        null=True,
        blank=True,
        default=None,
    )

    def __repr__(self):
        return f'<TAPApiEnvelope: id="{self.pk}", publishing_state={self.publishing_state}>'
