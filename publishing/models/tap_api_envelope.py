import logging

from django.db.models import DateTimeField
from django.db.models import Manager
from django.db.models import Q
from django.db.models import QuerySet
from django.db.transaction import atomic
from django_fsm import FSMField

from common.models.mixins import TimestampedMixin
from publishing.models import ProcessingState
from publishing.models.state import ApiPublishingState

logger = logging.getLogger(__name__)


# Exceptions
class ApiEnvelopeUnexpectedEnvelopeSequence(Exception):
    pass


class ApiEnvelopeInvalidWorkBasketStatus(Exception):
    pass


class TAPApiEnvelopeManager(Manager):
    @atomic
    def create(self, packaged_work_basket, **kwargs):
        """
        Create a new instance, from the packaged workbasket successfully
        processed.

         :param packaged_work_basket: packaged workbasket to publish.
        @throws ApiEnvelopeInvalidWorkBasketStatus if packaged workbasket isn't Successfully processed
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
        # TODO fix this is not working
        # if packaged_work_basket.envelope.envelope_id != Envelope.objects.last_envelope_id():
        #     raise ApiEnvelopeUnexpectedEnvelopeSequence(
        #         "Unable to create TAPApiEnvelope from PackagedWorkBasket instance "
        #         f"Envelope Id {packaged_work_basket.envelope.envelope_id} is not the next not expacted envelope",
        #     )
        envelope = super().create(**kwargs)

        # TODO create celery task to publish envelope to APIs
        return envelope


class ApiEnvelopeQuerySet(QuerySet):
    def published(self):
        return self.filter(
            publishing_state=ApiPublishingState.SUCCESSFULLY_PUBLISHED,
        )

    def unpublished(self):
        return self.filter(
            Q(
                publishing_state=ApiPublishingState.FAILED_PUBLISHING_STAGING,
            )
            | Q(
                publishing_state=ApiPublishingState.FAILED_PUBLISHING_PRODUCTION,
            )
            | Q(
                publishing_state=ApiPublishingState.AWAITING_PUBLISHING,
            ),
        )

    def currently_publishing(self):
        return self.filter(
            publishing_state=ApiPublishingState.CURRENTLY_PUBLISHING,
        )

    def successfully_published(self):
        return self.filter(
            publishing_state=ApiPublishingState.SUCCESSFULLY_PUBLISHED,
        )

    def failed_publishing(self):
        return self.filter(
            Q(
                publishing_state=ApiPublishingState.FAILED_PUBLISHING_STAGING,
            )
            | Q(
                publishing_state=ApiPublishingState.FAILED_PUBLISHING_PRODUCTION,
            ),
        )


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

    staging_published = DateTimeField(
        null=True,
        blank=True,
        default=None,
    )
    production_published = DateTimeField(
        null=True,
        blank=True,
        default=None,
    )

    def __repr__(self):
        return f'<TAPApiEnvelope: id="{self.pk}", publishing_state={self.publishing_state}>'
