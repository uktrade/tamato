from typing import List

from django.contrib.auth.models import User
from django.core.exceptions import MultipleObjectsReturned
from django.core.exceptions import ObjectDoesNotExist
from django.core.management import BaseCommand

from importer import models
from importer.chunker import chunk_taric
from importer.namespaces import TARIC_RECORD_GROUPS


def setup_batch(
    batch_name: str,
    author: User,
    split_on_code: bool,
    dependency_ids: List[str],
) -> models.ImportBatch:
    """
    Sets up a batch import.

    creating the ImportBatch object, and links the ImportBatch to any provided dependencies

    Args:
      batch_name: (str) The name to be stored against the import
      split_on_code: (bool) Indicate if the import should be split on record code
      dependency_ids: (list(str)) A list of batch ids(pks) that need to be imported before this batch can import.
      author: (User) The user to be listed as the creator of the file.

    Returns:
      ImportBatch instance, The created ImportBatch object.
    """

    batch = models.ImportBatch.objects.create(
        name=batch_name,
        author=author,
        split_job=split_on_code,
    )

    for dependency_id in dependency_ids or []:
        models.BatchDependencies.objects.create(
            depends_on=models.ImportBatch.objects.get(pk=dependency_id),
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
            "batch_name",
            help="The name of the batch (Envelope ID is recommended).",
            type=str,
        )
        parser.add_argument(
            "author",
            help="The email of the user that will be the author of the batch.",
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
            help="List of batches ids(pk) that need to finish before the current batch can run",
            action="append",
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
        user = self.validate_user(options["author"])

        batch = setup_batch(
            batch_name=options["batch_name"],
            author=user,
            split_on_code=options["split_codes"],
            dependencies=options["dependencies"],
        )
        with open(options["taric3_file"], "rb") as taric3_file:
            chunk_taric(
                taric3_file=taric3_file,
                batch=batch,
                record_group=options["commodities"],
            )

    def validate_user(self, username):
        """Validation to check that the username (email) corresponds to a
        user."""
        try:
            user = User.objects.get(email=username)
        except ObjectDoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    f'User with email "{username}" not found. Exiting.',
                ),
            )
            exit(1)
        except MultipleObjectsReturned:
            self.stdout.write(
                self.style.ERROR(
                    f'Multiple users found with email "{username}". Exiting.',
                ),
            )
            exit(1)
        return user
