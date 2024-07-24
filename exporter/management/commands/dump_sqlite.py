import logging
from typing import Any
from typing import Optional

from django.core.management import BaseCommand
from django.core.management.base import CommandParser

from exporter.sqlite.tasks import export_and_upload_sqlite

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Create a snapshot of the application database to a file in SQLite "
        "format. Snapshot file names take the form <transaction-order>.db, "
        "where <transaction-order> is the value of the last published "
        "transaction's order attribute. Care should be taken to ensure that "
        "there is sufficient local file system storage to accomodate the "
        "SQLite file - if you choose to target remote S3 storage, then a "
        "temporary local copy of the file will be created and cleaned up."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--asynchronous",
            action="store_const",
            help="Queue the snapshot task to run in an asynchronous process.",
            const=True,
            default=False,
        )
        parser.add_argument(
            "--save-local",
            help=(
                "Save the SQLite snapshot to the local file system under the "
                "(existing) directory given by DIRECTORY_PATH."
            ),
            dest="DIRECTORY_PATH",
        )
        return super().add_arguments(parser)

    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        logger.info(f"Triggering tariff database export to SQLite")

        local_path = options["DIRECTORY_PATH"]
        if options["asynchronous"]:
            export_and_upload_sqlite.delay(local_path)
        else:
            export_and_upload_sqlite(local_path)
