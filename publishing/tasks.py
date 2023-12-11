import logging
import time
from contextlib import contextmanager

import requests
from django.conf import settings
from django.core.cache import cache

from common.celery import app

logger = logging.getLogger(__name__)


@app.task(
    default_retry_delay=settings.ENVELOPE_GENERATION_DEFAULT_RETRY_DELAY,
    max_retries=settings.ENVELOPE_GENERATION_MAX_RETRIES,
    retry_backoff=True,
    retry_backoff_max=settings.ENVELOPE_GENERATION_RETRY_BACKOFF_MAX,
    retry_jitter=True,
    autoretry_for=(Exception,),
)
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
    from publishing.models import OperationalStatus
    from publishing.models import PackagedWorkBasket
    from publishing.models.envelope import ValidationState

    packaged_work_basket = PackagedWorkBasket.objects.get(
        pk=packaged_work_basket_id,
    )

    packaged_work_basket.envelope = Envelope.objects.create(
        packaged_work_basket=packaged_work_basket,
    )
    packaged_work_basket.save()

    if (
        packaged_work_basket.envelope.validation_state
        != ValidationState.SUCCESSFULLY_VALIDATED
    ):
        OperationalStatus.pause_queue(user=None)
        logger.error(
            f"Failed to successfully validate envelope "
            f"(Envelope={packaged_work_basket.envelope.pk}, "
            f"PackagedWorkBasket={packaged_work_basket.pk}, "
            f"WorkBasket={packaged_work_basket.workbasket.pk}) during envelope "
            f"creation process.",
        )
        logger.warning(
            f"Packaging queue paused due to envelope "
            f"(Envelope={packaged_work_basket.envelope.pk}) validation failure.",
        )
        return

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


@contextmanager
def publish_to_api_lock(lock_id):
    """
    Lock the Crown Dependencies publishing task.

    Lock will be removed once the task has returned or until the lock expires,
    whichever happens first.
    """
    # Lock expires in 10 minutes
    timeout_at = time.monotonic() + settings.CROWN_DEPENDENCIES_API_TASK_LOCK - 3
    status = cache.add(lock_id, "True", settings.CROWN_DEPENDENCIES_API_TASK_LOCK)
    try:
        yield status
    finally:
        if time.monotonic() < timeout_at and status:
            # Delete lock only if we acquired it
            cache.delete(lock_id)


class CrownDependenciesException(Exception):
    pass


@app.task(
    default_retry_delay=settings.CROWN_DEPENDENCIES_API_DEFAULT_RETRY_DELAY,
    max_retries=settings.CROWN_DEPENDENCIES_API_MAX_RETRIES,
    retry_backoff=True,
    retry_backoff_max=settings.CROWN_DEPENDENCIES_API_RETRY_BACKOFF_MAX,
    retry_jitter=True,
    autoretry_for=(CrownDependenciesException,),
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
    from publishing.models.state import CrownDependenciesPublishingState
    from publishing.tariff_api import get_tariff_api_interface

    interface = get_tariff_api_interface()

    def publish(packaged_workbasket: PackagedWorkBasket) -> requests.Response:
        """
        Publish envelope to Tariff API.

        If successful, transition `CrownDependenciesEnvelope` to `SUCCESSFULLY_PUBLISHED`.
        else, transition `CrownDependenciesEnvelope` to `FAILED_PUBLISHING`.
        @returns: response
        """
        logger.info(f"Publishing: {packaged_workbasket.crown_dependencies_envelope}")

        try:
            response = interface.post_envelope(envelope=packaged_workbasket.envelope)
        except requests.exceptions.Timeout:
            raise CrownDependenciesException("Tariff API timed out")
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

    def pause_queue_and_log_error(task: CrownDependenciesPublishingTask, message: str):
        """Pauses publishing queue by updating
        CrownDependenciesPublishingOperationalStatus user set to None as a
        system update."""
        logger.error(
            message,
        )
        CrownDependenciesPublishingOperationalStatus.pause_publishing(user=None)
        task.error = message
        task.save()

    # Lock task for its duration or until lock expires
    lock_id = f"{publish_to_api.name}-lock"
    with publish_to_api_lock(lock_id) as acquired:
        if not acquired:
            logger.info(
                "Skipping publishing task - task is still locked",
            )
            return

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
        else:
            logger.info("Nothing to publish, returning.")
            return

        if incomplete_envelopes:
            if len(incomplete_envelopes) > 1:
                message = """
                    Multiple CrownDependenciesEnvelope's in state CURRENTLY_PUBLISHING.
                    This is unexpected and requires remediation, pausing queue."""
                pause_queue_and_log_error(publishing_task, message)
                return
            publishing_envelope = incomplete_envelopes.first()
            packaged_workbasket = publishing_envelope.packagedworkbaskets.last()

            has_been_published = False
            if not publishing_envelope.published:
                # check if envelope posted to api

                try:
                    response = interface.get_envelope(
                        envelope_id=packaged_workbasket.envelope.envelope_id,
                    )
                except requests.exceptions.Timeout:
                    raise CrownDependenciesException("Tariff API timed out")
                if response.status_code == 200:
                    has_been_published = True
                elif response.status_code in [400, 404]:
                    has_been_published = False
                else:
                    publishing_task.error = response.text
                    publishing_task.save()
                    raise CrownDependenciesException(
                        "Unexpected response from Tariff API.",
                    )
            else:
                # Published but state not updated
                has_been_published = True

            if has_been_published:
                # it's been published but the object is not in the correct state
                logger.info(
                    f"Envelope: {packaged_workbasket.envelope.envelope_id}, already published."
                    "Updating status.",
                )
                publishing_envelope.publishing_succeeded()
            else:
                response = publish(packaged_workbasket)
                if response.status_code != 200:
                    publishing_task.error = response.text
                    publishing_task.save()
                    raise CrownDependenciesException(
                        "Unexpected response from Tariff API.",
                    )

        # Process unpublished packaged workbaskets
        for unpublished in unpublished_packaged_workbaskets:
            # checks if expected sequence
            if not unpublished.next_expected_to_api():
                message = f"""Cannot publish PackagedWorkBasket instance to tariff API,
                    Envelope Id {unpublished.envelope.envelope_id} is not the next not expected envelope.
                    Pausing Queue."""
                pause_queue_and_log_error(publishing_task, message)
                return

            CrownDependenciesEnvelope.objects.create(
                packaged_work_basket=unpublished,
            )
            unpublished.refresh_from_db()

            # publish to api
            response = publish(unpublished)
            if response.status_code != 200:
                publishing_task.error = response.text
                publishing_task.save()
                raise CrownDependenciesException("Unexpected response from Tariff API.")
        logger.info("No more envelopes to publish")
