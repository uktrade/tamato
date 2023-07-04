from typing import List
from typing import Sequence

from django.contrib.auth.models import User
from django.core.management import BaseCommand

from importer.management.commands.chunk_taric import chunk_taric
from importer.management.commands.chunk_taric import setup_batch
from importer.management.commands.run_import_batch import run_batch
from importer.management.util import ImporterCommandMixin
from importer.namespaces import TARIC_RECORD_GROUPS
from workbaskets.models import TRANSACTION_PARTITION_SCHEMES
from workbaskets.validators import WorkflowStatus


def import_taric(
    taric3_file: str,
    author: User,
    status: str,
    partition_scheme_setting: str,
    name: str,
    split_codes: bool = False,
    dependency_ids: List[int] = [],
    record_group: Sequence[str] = None,
):
    batch = setup_batch(
        batch_name=name,
        author=author,
        dependency_ids=dependency_ids,
        split_on_code=split_codes,
    )
    with open(taric3_file, "rb") as seed_file:
        batch = chunk_taric(seed_file, batch, record_group=record_group)

    run_batch(
        batch.pk,
        status,
        partition_scheme_setting,
        author.username,
        record_group=record_group,
    )


class Command(ImporterCommandMixin, BaseCommand):
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
            "author",
            help="The email of the user that will be the author of the batch.",
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
            help="List of batch IDs(pk) that need to finish before the current batch can run",
            type=int,
            action="append",
        )
        parser.add_argument(
            "-c",
            "--commodities",
            help="Only import commodities",
            action="store_true",
        )

    def handle(self, *args, **options):
        user = self.get_user(options["author"])
        record_group = (
            TARIC_RECORD_GROUPS["commodities"] if options["commodities"] else None
        )
        import_taric(
            taric3_file=options["taric3_file"],
            author=user,
            status=options["status"],
            partition_scheme_setting=options["partition_scheme"],
            name=options["name"],
            split_codes=options["split_codes"],
            dependency_ids=options["dependencies"],
            record_group=record_group,
        )
