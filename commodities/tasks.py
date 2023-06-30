from django.conf import settings

from common.celery import app
from importer.management.commands.run_import_batch import run_batch
from workbaskets.validators import WorkflowStatus


@app.task
def run_batch_task(
    batch_pk,
    username,
    record_group,
    workbasket_id=None,
    status=WorkflowStatus.EDITING,
    partition_scheme_setting=settings.TRANSACTION_SCHEMA,
):
    """Wraps the run_batch function in a celery task and updates the batch's
    status once complete."""

    run_batch(
        batch_id=batch_pk,
        status=status,
        partition_scheme_setting=partition_scheme_setting,
        username=username,
        record_group=record_group,
        workbasket_id=workbasket_id,
    )
