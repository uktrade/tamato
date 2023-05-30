import logging
from datetime import datetime

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
    """"""
    from publishing.models import TAPApiEnvelope
    from publishing.models.state import ApiPublishingState
    from publishing.tariff_api import get_tariff_api_interface

    logger.info("Starting Tariff API publishing task")

    interface = get_tariff_api_interface()

    def publish_to_staging() -> bool:
        """
        Publish envelope to Tariff API staging environment.

        If successful, update `staging_published` on `TAPApiEnvelope` and return
        `True`. Otheriwse transition to `FAILED_PUBLISHING_STAGING` and return
        `False`.
        """
        logger.info(f"Publishing to staging: {envelope}")
        if envelope.publishing_state == ApiPublishingState.AWAITING_PUBLISHING:
            envelope.begin_publishing()
        response = interface.post_envelope_staging(envelope=pwb_envelope)
        if response.status_code == 200:
            logger.info(f"Successfully published to staging: {envelope}")
            envelope.staging_published = datetime.now()
            envelope.save(update_fields=["staging_published"])
            return True
        else:
            logger.info(
                f"Failed publishing to staging: {envelope} - {response.text}",
            )
            if envelope.publishing_state == ApiPublishingState.CURRENTLY_PUBLISHING:
                envelope.publishing_staging_failed()
            return False

    def publish_to_production() -> bool:
        """
        Publish envelope to Tariff API production environment.

        If successful, update `published_to_tariffs_api` on `Envelope`,
        transition `TAPApiEnvelope` to `SUCCESSFULLY_PUBLISHED` and return
        `True`. Otherwise transition to `FAILED_PUBLISHING_PRODUCTION` and
        return `False`.
        """
        logger.info(f"Publishing to production: {envelope}")
        response = interface.post_envelope_production(envelope=pwb_envelope)
        if response.status_code == 200:
            logger.info(f"Successfully published to production: {envelope}")
            pwb_envelope.published_to_tariffs_api = datetime.now()
            pwb_envelope.save(update_fields=["published_to_tariffs_api"])
            envelope.publishing_succeeded()
            return True
        else:
            logger.info(
                f"Failed publishing to production: {envelope} - {response.text}",
            )
            if envelope.publishing_state in [
                ApiPublishingState.CURRENTLY_PUBLISHING,
                ApiPublishingState.FAILED_PUBLISHING_STAGING,
            ]:
                envelope.publishing_production_failed()
            return False

    def has_been_published() -> bool:
        """
        Check if an envelope has been published to Tariff API and attempt to
        publish it if not.

        Return True if an envelope has been published. Otherwise return False.
        """
        if not envelope.staging_published:
            response = interface.get_envelope_staging(
                envelope_id=pwb_envelope.envelope_id,
            )
            if response.status_code == 200:
                envelope.staging_published = datetime.now()
                envelope.save(update_fields=["staging_published"])
                return True if publish_to_production() else False
            else:
                return (
                    True if publish_to_staging() and publish_to_production() else False
                )
        elif not envelope.production_published:
            response = interface.get_envelope_production(
                envelope_id=pwb_envelope.envelope_id,
            )
            if response.status_code == 200:
                pwb_envelope.published_to_tariffs_api = datetime.now()
                pwb_envelope.save(update_fields=["published_to_tariffs_api"])
                envelope.publishing_succeeded()
                return True
            else:
                return True if publish_to_production() else False
        else:
            pwb_envelope.published_to_tariffs_api = datetime.now()
            pwb_envelope.save(update_fields=["published_to_tariffs_api"])
            envelope.publishing_succeeded()
            return True

    # Process unpublished envelopes
    envelopes_to_publish = TAPApiEnvelope.objects.unpublished().order_by("pk")
    if not envelopes_to_publish:
        logger.info("No envelopes to publish")
        return

    for envelope in envelopes_to_publish:
        if not envelope.can_publish():
            logger.info(
                f"Failed publishling to Tariff API: {envelope}. "
                f"The previous envelope is unpublished",
            )
            return

        pwb_envelope = envelope.packagedworkbaskets.last().envelope

        if envelope.publishing_state == ApiPublishingState.AWAITING_PUBLISHING:
            if publish_to_staging() and publish_to_production():
                # Publish next envelope in sequence
                continue
            return
        # Check published status of envelopes in these states in case
        # previous publishing task halted before transitioning state
        elif envelope.publishing_state in [
            ApiPublishingState.CURRENTLY_PUBLISHING,
            ApiPublishingState.FAILED_PUBLISHING_STAGING,
            ApiPublishingState.FAILED_PUBLISHING_PRODUCTION,
        ]:
            if has_been_published():
                continue
            else:
                return
