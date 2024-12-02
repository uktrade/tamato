import logging
from typing import Any
from typing import Optional

from django.core.management import BaseCommand
from django.core.management.base import CommandParser

from exporter.report_exporter.tasks import new_export_and_upload_quotas_csv

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Create a CSV of quotas for use within data workspace to produce the "
        "HMRC tariff open data CSV. The filename take the form "
        "quotas_export_<yyyymmdd>.csv. Care should be taken to ensure that "
        "there is sufficient local file system storage to accommodate the "
        "CSV file (although it should not be very large, less than 5MB "
        "(1.8MB at time of creation) - if you choose to target remote S3 "
        "storage, then a temporary local copy of the file will be created "
        "and cleaned up."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--asynchronous",
            action="store_const",
            help="Queue the CSV export task to run in an asynchronous process.",
            const=True,
            default=False,
        )
        parser.add_argument(
            "--save-local",
            help=(
                "Save the quotas CSV to the local file system under the "
                "(existing) directory given by DIRECTORY_PATH."
            ),
            dest="DIRECTORY_PATH",
        )
        return super().add_arguments(parser)

    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        logger.info(f"Triggering quotas export to CSV")

        local_path = options["DIRECTORY_PATH"]
        if options["asynchronous"]:
            new_export_and_upload_quotas_csv.delay(local_path)
        else:
            new_export_and_upload_quotas_csv(local_path)
