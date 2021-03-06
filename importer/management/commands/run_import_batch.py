from django.core.management import BaseCommand

from importer import models
from importer.tasks import find_and_run_next_batch_chunks
from workbaskets.validators import WorkflowStatus


def run_batch(batch: str, status: str, username: str):
    import_batch = models.ImportBatch.objects.get(name=batch)

    find_and_run_next_batch_chunks(import_batch, status, username)


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
                WorkflowStatus.NEW_IN_PROGRESS.value,
                WorkflowStatus.AWAITING_APPROVAL.value,
                WorkflowStatus.READY_FOR_EXPORT.value,
                WorkflowStatus.PUBLISHED.value,
            ],
            help="The status of the workbaskets containing the import changes.",
            type=str,
        )
        parser.add_argument(
            "-u",
            "--username",
            help="The username to use for the owner of the workbaskets created.",
            type=str,
        )

    def handle(self, *args, **options):
        run_batch(
            batch=options["batch"],
            status=options["status"],
            username=options["username"],
        )
