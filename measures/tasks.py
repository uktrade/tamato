import logging

from common.celery import app
from measures.models import MeasuresBulkCreator
from measures.models import MeasuresBulkEditor

logger = logging.getLogger(__name__)


@app.task
def bulk_create_measures(measures_bulk_creator_pk: int) -> None:
    """Bulk create measures from serialized measures form data saved within an
    instance of MeasuresBulkCreator."""

    measures_bulk_creator = MeasuresBulkCreator.objects.get(pk=measures_bulk_creator_pk)
    measures_bulk_creator.begin_processing()
    measures_bulk_creator.save()

    try:
        measures = measures_bulk_creator.create_measures()
    except Exception as e:
        measures_bulk_creator.processing_failed()
        measures_bulk_creator.save()
        logger.error(
            f"MeasuresBulkCreator({measures_bulk_creator.pk}) task failed "
            f"attempting to create measures in "
            f"WorkBasket({measures_bulk_creator.workbasket.pk}).",
        )
        raise e

    measures_bulk_creator.processing_succeeded()
    measures_bulk_creator.successfully_processed_count = len(measures)
    measures_bulk_creator.save()

    if measures:
        logger.info(
            f"MeasuresBulkCreator({measures_bulk_creator.pk}) task "
            f"succeeded in creating {len(measures)} Measures in "
            f"WorkBasket({measures_bulk_creator.workbasket.pk}).",
        )
    else:
        logger.info(
            f"MeasuresBulkCreator({measures_bulk_creator.pk}) task "
            f"succeeded but created no measures in "
            f"WorkBasket({measures_bulk_creator.workbasket.pk}).",
        )

@app.task
def bulk_edit_measures(measures_bulk_editor_pk: int) -> None:
    """Bulk edit measures from serialized measures form data saved within an
    instance of MeasuresBulkEditor."""

    measures_bulk_editor = MeasuresBulkEditor.objects.get(pk=measures_bulk_editor_pk)
    measures_bulk_editor.begin_processing()
    measures_bulk_editor.save()

    try:
        measures = measures_bulk_editor.edit_measures()
    except Exception as e:
        measures_bulk_editor.processing_failed()
        measures_bulk_editor.save()
        logger.error(
            f"MeasuresBulkCreator({measures_bulk_editor.pk}) task failed "
            f"attempting to edit measures in "
            f"WorkBasket({measures_bulk_editor.workbasket.pk}).",
        )
        raise e

    measures_bulk_editor.processing_succeeded()
    measures_bulk_editor.successfully_processed_count = len(measures)
    measures_bulk_editor.save()

    if measures:
        logger.info(
            f"MeasuresBulkEditoror({measures_bulk_editor.pk}) task "
            f"succeeded in editing {len(measures)} Measures in "
            f"WorkBasket({measures_bulk_editor.workbasket.pk}).",
        ) 