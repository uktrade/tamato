import logging

from common.celery import app
from measures.models import MeasuresBulkCreator

logger = logging.getLogger(__name__)


@app.task
def bulk_create_measures(measures_bulk_creator_pk: int) -> None:
    """Bulk create measures from serialized measures form data saved within an
    instance of MeasuresBulkCreator."""

    measures_bulk_creator = MeasuresBulkCreator.objects.get(pk=measures_bulk_creator_pk)
    measures = measures_bulk_creator.create_measures()

    if len(measures) > 0:
        transaction = measures[0].transaction
        workbasket = transaction.workbasket
        logger.info(
            f"MeasuresBulkCreator({measures_bulk_creator.pk}) created "
            f"{len(measures)} Measures in WorkBasket({workbasket.pk}) on "
            f"Transaction({transaction.pk}).",
        )
    else:
        logger.info(
            f"MeasuresBulkCreator {measures_bulk_creator.pk} created no " f"measures.",
        )
