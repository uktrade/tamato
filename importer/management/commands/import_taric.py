from typing import Sequence

from django.contrib.auth.models import User
from django.core.exceptions import MultipleObjectsReturned
from django.core.exceptions import ObjectDoesNotExist
from django.core.management import BaseCommand

from importer.management.commands.chunk_taric import chunk_taric
from importer.management.commands.chunk_taric import setup_batch
from importer.management.commands.run_import_batch import run_batch
from importer.namespaces import TARIC_RECORD_GROUPS
from workbaskets.models import TRANSACTION_PARTITION_SCHEMES
from workbaskets.validators import WorkflowStatus


def import_taric(
    taric3_file: str,
    username: str,
    status: str,
    partition_scheme_setting: str,
    name: str,
    split_codes: bool = False,
    dependencies=None,
    record_group: Sequence[str] = None,
):
    user = validate_user(username)
    batch = setup_batch(
        batch_name=name,
        author=user,
        dependencies=dependencies,
        split_on_code=split_codes,
    )
    with open(taric3_file, "rb") as seed_file:
        batch = chunk_taric(seed_file, batch, record_group=record_group)

    run_batch(
        batch.name,
        status,
        partition_scheme_setting,
        username,
        record_group=record_group,
    )


def validate_user(self, username):
    """Validation to check that the user_email corresponds to a user."""
    try:
        user = User.objects.get(username=username)
    except ObjectDoesNotExist:
        self.stdout.write(
            self.style.ERROR(
                f"Username not found. Exiting.",
            ),
        )
        exit(1)
    except MultipleObjectsReturned:
        self.stdout.write(
            self.style.ERROR(
                f"Multiple users found. Exiting.",
            ),
        )
        exit(1)
    return user


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
        parser.add_argument(
            "-c",
            "--commodities",
            help="Only import commodities",
            action="store_true",
        )

    def handle(self, *args, **options):
        record_group = (
            TARIC_RECORD_GROUPS["commodities"] if options["commodities"] else None
        )
        import_taric(
            taric3_file=options["taric3_file"],
            username=options["username"],
            status=options["status"],
            partition_scheme_setting=options["partition_scheme"],
            name=options["name"],
            split_codes=options["split_codes"],
            dependencies=options["dependencies"],
            record_group=record_group,
        )
