from typing import List

from django.core.management import BaseCommand

from importer import models
from importer.chunker import chunk_taric


def setup_batch(
    batch_name: str, split_on_code: bool, dependencies: List[str]
) -> models.ImportBatch:
    batch = models.ImportBatch.objects.create(name=batch_name, split_job=split_on_code)

    for dependency in dependencies or []:
        models.BatchDependencies.objects.create(
            depends_on=models.ImportBatch.objects.get(name=dependency),
            dependent_batch=batch,
        )

    return batch


class Command(BaseCommand):
    help = "Chunk data from a TARIC XML file into chunks for import"

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
        batch = setup_batch(
            options["name"], options["split_codes"], options["dependencies"]
        )
        with open(options["taric3_file"], "rb") as taric3_file:
            chunk_taric(
                taric3_file=taric3_file,
                batch=batch,
            )
