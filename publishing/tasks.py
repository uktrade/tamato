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


LOCK_EXPIRE = 60 * 10  # Lock expires in 10 minutes
API_TASK_LOCK = "crown_dependencies_lock"

# from contextlib import contextmanager
# from django.core.cache import cache
# from hashlib import md5
# from djangofeeds.models import Feed

# @contextmanager
# def memcache_lock(lock_id, oid):
#     timeout_at = time.monotonic() + LOCK_EXPIRE - 3
#     # cache.add fails if the key already exists
#     status = cache.add(lock_id, oid, LOCK_EXPIRE)
#     try:
#         yield status
#     finally:
#         # memcache delete is very slow, but we have to use it to take
#         # advantage of using add() for atomic locking
#         if time.monotonic() < timeout_at and status:
#             # don't release the lock if we exceeded the timeout
#             # to lessen the chance of releasing an expired lock
#             # owned by someone else
#             # also don't release the lock if we didn't acquire it
#             cache.delete(lock_id)


@app.task(
    default_retry_delay=settings.CROWN_DEPENDENCIES_API_DEFAULT_RETRY_DELAY,
    max_retries=settings.CROWN_DEPENDENCIES_API_MAX_RETRIES,
    retry_backoff=True,
    retry_backoff_max=settings.CROWN_DEPENDENCIES_API_RETRY_BACKOFF_MAX,
    retry_jitter=True,
)
def publish_to_api():
    """
    Task which takes a list (queue) of envelopes ready to publish.

    Iterates over publishing each item and will refresh the queryset to see if
    any new items have been added to the queue
    """
    from publishing.models import CrownDependenciesEnvelope
    from publishing.models import CrownDependenciesPublishingOperationalStatus
    from publishing.models import CrownDependenciesPublishingTask
    from publishing.models import PackagedWorkBasket
    from publishing.models.envelope import EnvelopeId
    from publishing.models.state import CrownDependenciesPublishingState
    from publishing.tariff_api import get_tariff_api_interface

    operational_status = (
        CrownDependenciesPublishingOperationalStatus.objects.current_status()
    )
    if (
        operational_status
        and operational_status.publishing_state
        == CrownDependenciesPublishingState.PAUSED
    ):
        logger.info(
            f"Skipping publishing task - "
            "publishing operational status="
            f"{operational_status.publishing_state}",
        )
        return

    logger.info("Starting Tariff API publishing task")

    interface = get_tariff_api_interface()

    def publish(packaged_workbasket: PackagedWorkBasket) -> object:
        """
        Publish envelope to Tariff API.

        If successful, transition `CrownDependenciesEnvelope` to `SUCCESSFULLY_PUBLISHED`.
        else, transition `CrownDependenciesEnvelope` to `FAILED_PUBLISHING`.
        @returns: response
        """
        interface = get_tariff_api_interface()
        logger.info(f"Publishing: {packaged_workbasket.crown_dependencies_envelope}")

        response = interface.post_envelope(envelope=packaged_workbasket.envelope)
        if response.status_code == 200:
            logger.info(
                f"Successfully published: {packaged_workbasket.crown_dependencies_envelope}",
            )
            packaged_workbasket.crown_dependencies_envelope.publishing_succeeded()
        else:
            logger.warn(
                f"Failed publishing: {packaged_workbasket.crown_dependencies_envelope} - {response.text}",
            )
            # send notification and updates state
            packaged_workbasket.crown_dependencies_envelope.publishing_failed()
        return response

    def has_been_published(
        envelope: CrownDependenciesEnvelope,
        envelope_id: EnvelopeId,
    ) -> bool:
        """
        Check if an envelope has been published to Tariff API.

        Return True if an envelope has been published. Otherwise return False.
        """
        if not envelope.published:
            response = interface.get_envelope(
                envelope_id=envelope_id,
            )
            if response.status_code != 200:
                return False

        return True

    # Get any unpublished crown dependency envelopes (can happen if a previous pubishing task failed)
    # State is ApiPublishingState.CURRENTLY_PUBLISHING or ApiPublishingState.FAILED_PUBLISHING,
    incomplete_envelopes = CrownDependenciesEnvelope.objects.unpublished()
    unpublished_packaged_workbaskets = (
        PackagedWorkBasket.objects.get_unpublished_to_api()
    )

    # Only create a record for tasks which publish something
    if incomplete_envelopes or unpublished_packaged_workbaskets:
        task_id = publish_to_api.request.id
        publishing_task = CrownDependenciesPublishingTask.objects.create(
            task_id=task_id,
        )
        # publishing_task.save()
    else:
        return

    if incomplete_envelopes:
        if len(incomplete_envelopes) > 1:
            logger.error(
                "Multiple CrownDependenciesEnvelope's in state CURRENTLY_PUBLISHING."
                "This is unexpected and requires remediation, pausing queue.",
            )
            # TODO update detail and pause queue
            CrownDependenciesPublishingOperationalStatus.pause_publishing(user=None)
            return
        publishing_envelope = incomplete_envelopes.first()
        packaged_workbasket = publishing_envelope.packagedworkbaskets.last()
        if has_been_published(
            publishing_envelope,
            packaged_workbasket.envelope.envelope_id,
        ):
            # it's been published but the object is not in the correct state
            logger.info(
                f"Envelope: {packaged_workbasket.envelope.envelope_id}, already published."
                "Updating status.",
            )
            publishing_envelope.publishing_succeeded()
        else:
            response = publish(packaged_workbasket)
            if response.status_code != 200:
                # update error details
                # stop processsing!!!
                return

    # Process unpublished packaged workbaskets
    for unpublished in unpublished_packaged_workbaskets:
        # checks if expected sequence
        if not unpublished.can_publish_to_crown_dependencies():
            logger.error(
                "Cannot publish PackagedWorkBasket instance to tariff API "
                f"Envelope Id {unpublished.envelope.envelope_id} is not the next not expected envelope."
                "Pausing Queue.",
            )
            # TODO update task with error detail, pause and EXIT (paused because the next run will also fail)
            CrownDependenciesPublishingOperationalStatus.pause_publishing(user=None)
            return

        unpublished.create_crown_dependencies_envelope()

        # publish to api
        response = publish(unpublished)
        if response.status_code != 200:
            # update error details
            # stop processsing!!!
            return
    else:
        logger.info("No envelopes to publish")
