from django.conf import settings
from django.http import HttpResponseRedirect
from rest_framework.reverse import reverse

from common.celery import app
from importer import models
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

    batch = models.ImportBatch.objects.get(pk=batch_pk)

    run_batch(
        batch=batch,
        status=status,
        partition_scheme_setting=partition_scheme_setting,
        username=username,
        record_group=record_group,
        workbasket_id=workbasket_id,
    )

    # Change the status to Imported once successful
    batch.imported()
    batch.save()

    HttpResponseRedirect(reverse("commodity-ui-import-success"))
