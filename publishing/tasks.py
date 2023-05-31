import logging

from django.conf import settings

from common.celery import app

logger = logging.getLogger(__name__)


@app.task
def create_xml_envelope_file(
    packaged_work_basket_id: int,
    notify_when_done: bool = True,
):
    """
    Create an XML envelope and save to the configured backing store (normally
    S3). Once creation and saving has completed successfully, and
    `notify_when_done` is True, then notify users that the envelope is ready for
    processing.

    There are three cases when a PackagedWorkBasket instance requires its
    envelope generating:

    1. When this instance is created at queue position 1 and no other
    PackagedWorkBasket is being processed - i.e.
    PackagedWorkBasketQuerySet.currently_processing() returns no instances.

    2. When this instance is moved to queue position 1 and no other
    PackagedWorkBasket is being processed -
    PackagedWorkBasketQuerySet.currently_processing() returns no instances.

    3. When some other top-most instance has its PackagedWorkBasket.state
    transitioned to either SUCCESSFULLY_PROCESSED or FAILED_PROCESSING, and
    this instance (with state == ProcessingState.AWAITING_PROCESSING)
    becomes the new top-most instance.


    If the Celery process used to execute this function fails, then this
    function may be called again in order to generate the envelope.
    """
    from publishing.models import Envelope
    from publishing.models import PackagedWorkBasket

    packaged_work_basket = PackagedWorkBasket.objects.get(
        pk=packaged_work_basket_id,
    )

    packaged_work_basket.envelope = Envelope.objects.create(
        packaged_work_basket=packaged_work_basket,
    )
    packaged_work_basket.save()

    if notify_when_done:
        packaged_work_basket.notify_ready_for_processing()


def schedule_create_xml_envelope_file(
    packaged_work_basket,
    notify_when_done: bool = True,
    seconds_delay: int = 0,
):
    """
    Schedule creating and storing the envelope file and associating it with
    packaged_work_basket.

    If notify_when_done is True, then notification emails are sent after
    envelope generation completes.

    If seconds_delay is set to a positive value, then schdeuling is delayed by
    that number of seconds. This seems to be necessary when scheduling in the
    same process context as a database save / update operationi (for instance
    when creating a new top-most PackagedWorkBasket instance), since otherwise
    the operation can fail.
    """
    if packaged_work_basket.envelope and packaged_work_basket.envelope.deleted is True:
        logger.info(
            f"Envelope deleted, Not scheduling envelope creation for",
            f"packaged_work_basket.id={packaged_work_basket.pk} ",
        )
    else:
        task = create_xml_envelope_file.apply_async(
            (packaged_work_basket.pk, notify_when_done),
            countdown=seconds_delay,
        )
        logger.info(
            f"Creating XML envelope file for packaged_work_basket.id="
            f"{packaged_work_basket.pk} on task.id={task.id}.",
        )
        packaged_work_basket.create_envelope_task_id = task.id
        packaged_work_basket.save()


@app.task(
    default_retry_delay=settings.CHANNEL_ISLANDS_API_DEFAULT_RETRY_DELAY,
    max_retries=settings.CHANNEL_ISLANDS_API_MAX_RETRIES,
    retry_backoff=True,
    retry_backoff_max=settings.CHANNEL_ISLANDS_API_RETRY_BACKOFF_MAX,
    retry_jitter=True,
)
def publish_to_api():
    """
    Task which takes a list (queue) of envelopes ready to publish.

    Iterates over publishing each item and will refresh the queryset to see if
    any new items have been added to the queue ( envelopes in the
    AWAITING_PUBLISHING state)
    """
    from publishing.models import CrownDependenciesEnvelope
    from publishing.models import Envelope
    from publishing.models.state import ApiPublishingState
    from publishing.tariff_api import get_tariff_api_interface

    logger.info("Starting Tariff API publishing task")

    interface = get_tariff_api_interface()

    class APIPublishingIterator:
        def __init__(self, queryset) -> None:
            self.initial_queryset = queryset
            self.queryset = queryset.all()
            self.index = 0

        def __iter__(self):
            return self

        def __next__(self) -> bool:
            if self.index >= len(self.queryset):
                self.queryset = self.refresh_queryset()
                self.index = 0
                if not self.queryset:
                    logger.info("No more envelopes to publish")
                    raise StopIteration

            envelope = self.queryset[self.index]

            if not envelope.can_publish():
                logger.warn(
                    f"Failed publishling to Tariff API: {envelope}. "
                    f"The previous envelope is unpublished",
                )
                raise StopIteration

            pwb_envelope = envelope.packagedworkbaskets.last().envelope

            if envelope.publishing_state in [
                ApiPublishingState.AWAITING_PUBLISHING,
                ApiPublishingState.FAILED_PUBLISHING,
            ]:
                response = publish(envelope, pwb_envelope)
                if not response:
                    raise StopIteration
            # Check published status of envelopes in these states in case
            # previous publishing task halted before transitioning state
            elif envelope.publishing_state == ApiPublishingState.CURRENTLY_PUBLISHING:
                if not has_been_published(envelope, pwb_envelope):
                    response = publish(envelope, pwb_envelope)
                    if not response:
                        raise StopIteration
                else:
                    # has been published but stuck in currently publishing
                    # transition and move on
                    envelope.publishing_succeeded()
                    response = True

            self.index += 1
            return response

        def refresh_queryset(self):
            return self.initial_queryset.all()

    def publish(envelope: CrownDependenciesEnvelope, pwb_envelope: Envelope) -> bool:
        """
        Publish envelope to Tariff API.

        If successful, update `published_to_tariffs_api` on `Envelope`,
        transition `CrownDependenciesEnvelope` to `SUCCESSFULLY_PUBLISHED` and
        return `True`. Otherwise transition to `FAILED_PUBLISHING` and return
        `False`.
        """
        logger.info(f"Publishing: {envelope}")
        if envelope.publishing_state == ApiPublishingState.AWAITING_PUBLISHING:
            envelope.begin_publishing()
        response = interface.post_envelope(envelope=pwb_envelope)
        if response.status_code == 200:
            logger.info(f"Successfully published: {envelope}")
            envelope.publishing_succeeded()
            return True
        else:
            logger.warn(
                f"Failed publishing: {envelope} - {response.text}",
            )
            if envelope.publishing_state == ApiPublishingState.CURRENTLY_PUBLISHING:
                envelope.publishing_failed()
            return False

    def has_been_published(
        envelope: CrownDependenciesEnvelope,
        pwb_envelope: Envelope,
    ) -> bool:
        """
        Check if an envelope has been published to Tariff API and attempt to
        publish it if not.

        Return True if an envelope has been published. Otherwise return False.
        """
        if not envelope.published:
            response = interface.get_envelope(
                envelope_id=pwb_envelope.envelope_id,
            )
            if response.status_code != 200:
                return False

        return True

    # Process unpublished envelopes
    envelopes_to_publish = CrownDependenciesEnvelope.objects.unpublished().order_by(
        "pk",
    )

    api_iterator = APIPublishingIterator(envelopes_to_publish)

    for result in api_iterator:
        # loop through and process
        continue
