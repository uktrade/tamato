from typing import Sequence

from django.core.management import BaseCommand

from importer import models
from importer.namespaces import TARIC_RECORD_GROUPS
from importer.tasks import find_and_run_next_batch_chunks
from workbaskets.models import TRANSACTION_PARTITION_SCHEMES
from workbaskets.validators import WorkflowStatus


def run_batch(
    batch: str,
    status: str,
    partition_scheme_setting: str,
    username: str,
    workbasket_id: str = None,
    record_group: Sequence[str] = None,
):
    import_batch = models.ImportBatch.objects.get(name=batch)

    find_and_run_next_batch_chunks(
        import_batch,
        workbasket_id,
        status,
        partition_scheme_setting,
        username,
        record_group=record_group,
    )


class Command(BaseCommand):
    help = "Import data from a TARIC XML file into TaMaTo"

    def add_arguments(self, parser):
        parser.add_argument(
            "batch",
            help="The batch Id to be imported",
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
        run_batch(
            batch=options["batch"],
            status=options["status"],
            partition_scheme_setting=options["partition_scheme"],
            username=options["username"],
            record_group=options["commodities"],
        )
