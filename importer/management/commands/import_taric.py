from django.core.management import BaseCommand

from importer.management.commands.chunk_taric import chunk_taric
from importer.management.commands.chunk_taric import setup_batch
from importer.management.commands.run_import_batch import run_batch
from workbaskets.validators import WorkflowStatus


def import_taric(
    taric3_file, username, status, name, split_codes: bool = False, dependencies=None
):
    batch = setup_batch(
        batch_name=name, dependencies=dependencies, split_on_code=split_codes
    )
    with open(taric3_file, "rb") as seed_file:
        batch = chunk_taric(seed_file, batch)

    run_batch(batch.name, username, status)


class Command(BaseCommand):
    help = "Import data from a TARIC XML file into TaMaTo"

    def add_arguments(self, parser):
        parser.add_argument(
            "taric3_file",
            help="The TARIC3 file to be parsed.",
            type=str,
        )
        parser.add_argument(
            "name",
            help="The name of the batch, the Envelope ID is recommended.",
            type=str,
        )
        parser.add_argument(
            "-u",
            "--username",
            help="The username to use for the owner of the workbaskets created.",
            type=str,
        )
        parser.add_argument(
            "-S",
            "--status",
            choices=[
                WorkflowStatus.NEW_IN_PROGRESS.value,
                WorkflowStatus.AWAITING_APPROVAL.value,
                WorkflowStatus.READY_FOR_EXPORT.value,
                WorkflowStatus.PUBLISHED.value,
            ],
            help="The status of the workbaskets containing the import changes.",
            type=str,
        )
        parser.add_argument(
            "-s",
            "--split-codes",
            help="Split the file based on record codes",
            action="store_true",
        )
        parser.add_argument(
            "-d",
            "--dependencies",
            help="List of batches that need to finish before the current batch can run",
            action="append",
        )

    def handle(self, *args, **options):
        import_taric(
            taric3_file=options["taric3_file"],
            username=options["username"],
            name=options["name"],
            status=options["status"],
            split_codes=options["split_codes"],
            dependencies=options["dependencies"],
        )
