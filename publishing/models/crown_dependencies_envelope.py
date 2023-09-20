import logging
from datetime import datetime

from django.db.models import DateTimeField
from django.db.models import Manager
from django.db.models import QuerySet
from django.db.transaction import atomic
from django_fsm import FSMField
from django_fsm import transition

from common.models.mixins import TimestampedMixin
from notifications.models import CrownDependenciesEnvelopeFailedNotification
from notifications.models import CrownDependenciesEnvelopeSuccessNotification
from publishing.models.decorators import save_after
from publishing.models.decorators import skip_notifications_if_disabled
from publishing.models.packaged_workbasket import PackagedWorkBasket
from publishing.models.state import ApiPublishingState
from publishing.models.state import ProcessingState

logger = logging.getLogger(__name__)


# Exceptions


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
        """
        if (
            packaged_work_basket.processing_state
            != ProcessingState.SUCCESSFULLY_PROCESSED
        ):
            raise ApiEnvelopeInvalidWorkBasketStatus(
                "Unable to create CrownDependenciesEnvelope from PackagedWorkBasket instance "
                f"PackagedWorkBasket status not successful, {packaged_work_basket.processing_state} status.",
            )

        envelope = super().create(**kwargs)

        packaged_work_basket.crown_dependencies_envelope = envelope
        packaged_work_basket.save()
        return envelope


class CrownDependenciesEnvelopeQuerySet(QuerySet):
    def unpublished(self) -> "CrownDependenciesEnvelopeQuerySet":
        return self.failed_publishing() | self.currently_publishing()

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

    This model contains the Envelope upload status to the Channel islands API
    and it's publishing times.

    An Envelope contains one or more Transactions, listing changes to be applied
    to the tariff in the sequence defined by the transaction IDs. Contains
    xml_file which is a reference to the envelope stored on s3. This can be
    found in the Envelope model.
    """

    class Meta:
        ordering = ("pk",)

    objects: CrownDependenciesEnvelopeQuerySet = (
        CrownDependenciesEnvelopeManager.from_queryset(
            CrownDependenciesEnvelopeQuerySet,
        )()
    )

    publishing_state = FSMField(
        default=ApiPublishingState.CURRENTLY_PUBLISHING,
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

    def __repr__(self) -> str:
        return f'<CrownDependenciesEnvelope: id="{self.pk}", publishing_state={self.publishing_state}>'

    def previous_envelope(self) -> CrownDependenciesEnvelopeQuerySet:
        """Get the previous `CrownDependenciesEnvelope` by order of `pk`."""
        try:
            return CrownDependenciesEnvelope.objects.filter(pk__lt=self.pk).last()
        except CrownDependenciesEnvelope.DoesNotExist:
            return None

    # publishing_state transition management

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
        self.notify_publishing_success()

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
        self.notify_publishing_failed()

    @skip_notifications_if_disabled
    def notify_publishing_success(self):
        """Notify users that an envelope has successfully publishing to api."""

        notification = CrownDependenciesEnvelopeSuccessNotification(
            notified_object_pk=self.pk,
        )
        print(notification)
        notification.save()
        notification.schedule_send_emails()

    @skip_notifications_if_disabled
    def notify_publishing_failed(self):
        """Notify users that an envelope has failed publishing to api."""

        notification = CrownDependenciesEnvelopeFailedNotification(
            notified_object_pk=self.pk,
        )
        notification.save()
        notification.schedule_send_emails()

    @atomic
    def refresh_from_db(self, using=None, fields=None):
        """Reload instance from database but avoid writing to
        self.publishing_state directly in order to avoid the exception
        'AttributeError: Direct publishing_state modification is not
        allowed.'."""
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
