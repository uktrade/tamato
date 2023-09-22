from django.core.management import BaseCommand

from importer import models
from importer.namespaces import TARIC_RECORD_GROUPS
from importer.tasks import new_import_chunk
from workbaskets.models import TRANSACTION_PARTITION_SCHEMES
from workbaskets.validators import WorkflowStatus


def new_run_batch(
    batch_id: int,
    partition_scheme_setting: str,
    username: str,
    workbasket_id: str = None,
):
    import_batch = models.ImportBatch.objects.get(pk=batch_id)

    new_import_chunk.delay(
        chunk_pk=import_batch.chunks.first().pk,
        workbasket_id=workbasket_id,
        partition_scheme_setting=partition_scheme_setting,
        username=username,
    )


class Command(BaseCommand):
    help = "Import data from a TARIC XML file into TaMaTo with new importer"

    def add_arguments(self, parser):
        parser.add_argument(
            "batch_id",
            help="The batch Id(pk) to be imported",
            type=str,
        )
        parser.add_argument(
            "-s",
            "--status",
            choices=[
                WorkflowStatus.EDITING.value,
                WorkflowStatus.QUEUED.value,
                WorkflowStatus.PUBLISHED.value,
            ],
            help="The status of the workbaskets containing the import changes.",
            type=str,
        )
        parser.add_argument(
            "-p",
            "--partition-scheme",
            choices=TRANSACTION_PARTITION_SCHEMES.keys(),
            help="Partition to place transactions in approved workbaskets",
            type=str,
        )
        parser.add_argument(
            "-u",
            "--username",
            help="The username to use for the owner of the workbaskets created.",
            type=str,
        )
        parser.add_argument(
            "-C",
            "--commodities",
            help="Only import commodities",
            action="store_const",
            const=TARIC_RECORD_GROUPS["commodities"],
            default=None,
        )

    def handle(self, *args, **options):
        new_run_batch(
            batch_id=options["batch_id"],
            status=options["status"],
            partition_scheme_setting=options["partition_scheme"],
            username=options["username"],
            record_group=options["commodities"],
        )
