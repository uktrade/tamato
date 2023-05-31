import logging
from datetime import datetime

from celery.result import AsyncResult
from django.db.models import CharField
from django.db.models import DateTimeField
from django.db.models import Manager
from django.db.models import Max
from django.db.models import Q
from django.db.models import QuerySet
from django.db.transaction import atomic
from django_fsm import FSMField
from django_fsm import transition

from common.models.mixins import TimestampedMixin
from publishing.models.envelope import Envelope
from publishing.models.packaged_workbasket import PackagedWorkBasket
from publishing.models.state import ApiPublishingState
from publishing.models.state import ProcessingState

logger = logging.getLogger(__name__)


# Decorators


def save_after(func):
    """Decorator used to save CrownDependenciesEnvelope instances after a state
    transition."""

    @atomic
    def inner(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        self.save()
        return result

    return inner


# Exceptions
class ApiEnvelopeUnexpectedEnvelopeSequence(Exception):
    pass


class ApiEnvelopeInvalidWorkBasketStatus(Exception):
    pass


class CrownDependenciesEnvelopeManager(Manager):
    @atomic
    def create(
        self, packaged_work_basket: PackagedWorkBasket, **kwargs
    ) -> "CrownDependenciesEnvelope":
        """
        Create a new instance, from the packaged workbasket successfully
        processed.

         :param packaged_work_basket: packaged workbasket to publish.
        @throws ApiEnvelopeInvalidWorkBasketStatus if packaged workbasket isn't Successfully processed
        @throws ApiEnvelopeAlreadyExists if packaged workbasket already has a CrownDependenciesEnvelope
        @throws ApiEnvelopeUnexpectedEnvelopeSequence if packaged workbasket isn't expected envelope id
        """
        if (
            packaged_work_basket.processing_state
            != ProcessingState.SUCCESSFULLY_PROCESSED
        ):
            raise ApiEnvelopeInvalidWorkBasketStatus(
                "Unable to create CrownDependenciesEnvelope from PackagedWorkBasket instance "
                f"PackagedWorkBasket status not successful, {packaged_work_basket.processing_state} status.",
            )

        previous_id = (
            PackagedWorkBasket.objects.select_related(
                "envelope",
                "crown_dependencies_envelope",
            )
            .filter(
                Q(
                    envelope__id__isnull=False,
                    envelope__published_to_tariffs_api__isnull=False,
                )
                | Q(crown_dependencies_envelope__id__isnull=False),
            )
            .aggregate(
                Max("envelope__envelope_id"),
            )["envelope__envelope_id__max"]
        )
        """Join PackagedWorkBasket with Envelope and CrownDependenciesEnvelope
        model selecting objects Where an Envelope model exists and the
        published_to_tariffs_api field is not null Or Where a
        CrownDependenciesEnvelope is not null Then select the max value for ther
        envelope_id field in the Envelope instance."""

        if packaged_work_basket.envelope.envelope_id[2:] == "0001":
            year = int(packaged_work_basket.envelope.envelope_id[:2])
            last_envelope = Envelope.objects.for_year(year=year - 1).last()
            # uses None if first envelope (no previous ones)
            expected_previous_id = last_envelope.envelope_id if last_envelope else None
        else:
            expected_previous_id = str(
                int(packaged_work_basket.envelope.envelope_id) - 1,
            )

        if previous_id and previous_id != expected_previous_id:
            raise ApiEnvelopeUnexpectedEnvelopeSequence(
                "Unable to create CrownDependenciesEnvelope from PackagedWorkBasket instance "
                f"Envelope Id {packaged_work_basket.envelope.envelope_id} is not the next not expected envelope",
            )
        envelope = super().create(**kwargs)

        return envelope


class CrownDependenciesEnvelopeQuerySet(QuerySet):
    def awaiting_publishing(self) -> "CrownDependenciesEnvelopeQuerySet":
        return self.filter(
            publishing_state=ApiPublishingState.AWAITING_PUBLISHING,
        )

    def unpublished(self) -> "CrownDependenciesEnvelopeQuerySet":
        return (
            self.failed_publishing()
            | self.awaiting_publishing()
            | self.currently_publishing()
        )

    def currently_publishing(self) -> "CrownDependenciesEnvelopeQuerySet":
        return self.filter(
            publishing_state=ApiPublishingState.CURRENTLY_PUBLISHING,
        )

    def published(self) -> "CrownDependenciesEnvelopeQuerySet":
        return self.filter(
            publishing_state=ApiPublishingState.SUCCESSFULLY_PUBLISHED,
        )

    def failed_publishing(self) -> "CrownDependenciesEnvelopeQuerySet":
        return self.filter(
            publishing_state=ApiPublishingState.FAILED_PUBLISHING,
        )


class CrownDependenciesEnvelope(TimestampedMixin):
    """
    Represents a crown dependencies envelope.

    This model contains the Envelope upload status to the Channel islands API and it's publishing times.

    An Envelope contains one or more Transactions, listing changes to be applied
    to the tariff in the sequence defined by the transaction IDs. Contains
    xml_file which is a reference to the envelope stored on s3. This can be found in the Envelope model.
    """

    class Meta:
        ordering = ("pk",)

    objects: CrownDependenciesEnvelopeQuerySet = (
        CrownDependenciesEnvelopeManager.from_queryset(
            CrownDependenciesEnvelopeQuerySet,
        )()
    )

    publishing_state = FSMField(
        default=ApiPublishingState.AWAITING_PUBLISHING,
        choices=ApiPublishingState.choices,
        db_index=True,
        protected=True,
        editable=False,
    )

    published = DateTimeField(
        null=True,
        blank=True,
        default=None,
    )

    publishing_task_id = CharField(
        max_length=50,
        null=True,
        blank=True,
        unique=True,
    )

    def __repr__(self) -> str:
        return f'<CrownDependenciesEnvelope: id="{self.pk}", publishing_state={self.publishing_state}>'

    def terminate_publishing_task(self):
        """Terminate the envelope's publishing task as identified by its
        publishing_task_id."""
        logger.info(
            f"Attempting publishing task termination for envelope pk={self.pk}.",
        )
        if not self.publishing_task_id:
            logger.info(
                f"Unable to terminate publishing task for envelope "
                f"pk={self.pk} - "
                f"empty publishing_task_id.",
            )
            return

        task_result = AsyncResult(self.publishing_task_id)
        if not task_result:
            logger.info(
                f"Unable to terminate publishing task for envelope "
                f"pk={self.pk}, "
                f"publishing_task_id={self.publishing_task_id} - "
                f"task result is unavailable.",
            )
            return

        task_result.revoke()
        self.publishing_task_id = None
        self.save()
        logger.info(
            f"Terminated publishing task for envelope pk={self.pk}.",
        )

    @property
    def publishing_task_status(self):
        """Return the status of the envelope's publishing task if it is
        available, otherwise return None."""
        if not self.publishing_task_id:
            return None
        task_result = AsyncResult(self.publishing_task_id)
        if not task_result:
            return None
        return task_result.status

    def previous_envelope(self) -> CrownDependenciesEnvelopeQuerySet:
        """Get the previous `CrownDependenciesEnvelope` by order of `pk`."""
        try:
            return CrownDependenciesEnvelope.objects.get(pk=self.pk - 1)
        except CrownDependenciesEnvelope.DoesNotExist:
            return None

    def can_publish(self) -> bool:
        """Conditional check if the previous `CrownDependenciesEnvelope` has
        been `SUCCESSFULLY_PUBLISHED`."""
        previous_envelope = self.previous_envelope()
        if (
            previous_envelope
            and previous_envelope.publishing_state
            == ApiPublishingState.SUCCESSFULLY_PUBLISHED
            or not previous_envelope
        ):
            return True
        else:
            return False

    # publishing_state transition management

    @save_after
    @transition(
        field=publishing_state,
        source=ApiPublishingState.AWAITING_PUBLISHING,
        target=ApiPublishingState.CURRENTLY_PUBLISHING,
        custom={"label": "Begin publishing"},
    )
    def begin_publishing(self):
        """Begin publishing a `CrownDependenciesEnvelope` to the Tariff API."""

    @save_after
    @transition(
        field=publishing_state,
        source=[
            ApiPublishingState.FAILED_PUBLISHING,
            ApiPublishingState.CURRENTLY_PUBLISHING,
        ],
        target=ApiPublishingState.SUCCESSFULLY_PUBLISHED,
        custom={"label": "Publishing succeeded"},
    )
    def publishing_succeeded(self):
        """Publishing a `CrownDependenciesEnvelope` to the Tariff API completed
        with a successful outcome."""
        self.published = datetime.now()

    @save_after
    @transition(
        field=publishing_state,
        source=ApiPublishingState.CURRENTLY_PUBLISHING,
        target=ApiPublishingState.FAILED_PUBLISHING,
        custom={"label": "Publishing failed"},
    )
    def publishing_failed(self):
        """Publishing a `CrownDependenciesEnvelope` to the Tariff API completed
        with a failed outcome."""

    @atomic
    def refresh_from_db(self, using=None, fields=None):
        """Reload instance from database but avoid writing to
        self.publishing_state directly in order to avoid the exception
        'AttributeError: Direct publishing_state modification is not allowed.'
        """
        if fields is None:
            refresh_state = True
            fields = [f.name for f in self._meta.concrete_fields]
        else:
            refresh_state = "publishing_state" in fields

        fields_without_state = [f for f in fields if f != "publishing_state"]

        super().refresh_from_db(using=using, fields=fields_without_state)

        if refresh_state:
            new_state = (
                type(self)
                .objects.only("publishing_state")
                .get(pk=self.pk)
                .publishing_state
            )
            self._meta.get_field("publishing_state").set_state(self, new_state)
