import logging

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

    # TODO: Consider chaining this task from schedule_create_xml_envelope_file().
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
