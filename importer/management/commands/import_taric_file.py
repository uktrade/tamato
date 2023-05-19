from datetime import datetime

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import BaseCommand

from importer.management.commands.chunk_taric import chunk_taric
from importer.management.commands.chunk_taric import setup_batch
from importer.management.commands.run_import_batch import run_batch
from importer.namespaces import TARIC_RECORD_GROUPS
from workbaskets.models import TRANSACTION_PARTITION_SCHEMES
from workbaskets.validators import WorkflowStatus


def import_taric_file(
    taric_file: str,
    user: User,
    workbasket_id=None,
    record_group=TARIC_RECORD_GROUPS["commodities"],
    status=WorkflowStatus.EDITING,
    partition_scheme_setting=settings.TRANSACTION_SCHEMA,
):
    # create time stamp for batch name
    now = datetime.now()
    current_time = now.strftime("%H%M%S")

    # Create batch for import
    batch = setup_batch(
        batch_name=f"{taric_file.name}_{current_time}",
        author=user,
        dependencies=[],
        split_on_code=False,
    )

    # Run commands to process the file
    chunk_taric(taric_file, batch, record_group=record_group)
    run_batch(
        batch=batch.name,
        status=status,
        partition_scheme_setting=partition_scheme_setting,
        username=user.username,
        record_group=record_group,
        workbasket_id=workbasket_id,
    )


class Command(BaseCommand):
    help = "Import data from an EU TARIC XML file into Tamato"

    def add_arguments(self, parser):
        parser.add_argument(
            "taric_file",
            help="The TARIC3 file to be parsed.",
            type=str,
        )
        parser.add_argument(
            "-u",
            "--user",
            help="The user to use for the owner of the workbaskets created, and the author of the batch.",
            type=str,
        )
        parser.add_argument(
            "-S",
            "--status",
            choices=WorkflowStatus.values,
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

    def handle(self, *args, **options):
        import_taric_file(
            taric_file=options["taric3_file"],
            user=options["user"],
            workbasket_id=options["workbasket_id"],
            record_group=options["record_group"],
            status=options["status"],
            partition_scheme_setting=options["partition_scheme"],
        )
