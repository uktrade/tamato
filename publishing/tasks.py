import logging

from common.celery import app

logger = logging.getLogger(__name__)


@app.task
def create_xml_envelope_file(
    packaged_work_basket_id,
    notify_when_done: bool,
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
    PackagedWorkBasket is being processed - i.e.
    PackagedWorkBasketQuerySet.currently_processing() returns no instances.

    3. When some other top-most instance has its PackagedWorkBasket.state
    transitioned to either SUCCESSFULLY_PROCESSED or FAILED_PROCESSING, and
    this instance (with state == ProcessingState.AWAITING_PROCESSING)
    becomes the new top-most instance.

    TODO: Implement action 2.

    If the Celery process used to execute this function fails, then this
    function may be called again in order to generate the envelope.
    """

    from publishing.models import PackagedWorkBasket

    packaged_work_basket = PackagedWorkBasket.objects.get(
        packaged_work_basket_id,
    )

    # TODO: Dump workbasket transactions to XML envelope file and save to S3.

    if notify_when_done:
        packaged_work_basket.notify_ready_for_processing()


def schedule_create_xml_envelope_file(
    packaged_work_basket,
    notify_when_done: bool = True,
):
    task = create_xml_envelope_file.delay(
        packaged_work_basket.pk,
        notify_when_done,
    )
    logger.info(
        f"Creating XML envelope file for packaged_work_basket.id="
        f"{packaged_work_basket.pk} on task.id={task.id}.",
    )
    packaged_work_basket.create_envelope_task_id = task.id
    packaged_work_basket.save()
