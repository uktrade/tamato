import logging

from django.core.management.base import BaseCommand

from open_data.reports.commodities import create_commodities_report
from open_data.reports.measures import create_measure_as_defined_report

logger = logging.getLogger(__name__)


REPORT_TYPE = {
    "MAD": create_measure_as_defined_report,
    "COMMODITIES": create_commodities_report,
}


class Command(BaseCommand):

    help = "Refresh report data. Allowed types are - All - {}".format(
        " - ".join(REPORT_TYPE.keys()),
    )
    arg_name = "what"

    def add_arguments(self, parser):
        # Positional arguments, default to All for no argument
        parser.add_argument(self.arg_name, nargs="*", default=["All"])

    def handle(self, *args, **options):
        for arg in options[self.arg_name]:
            if arg.upper() == "ALL":
                logger.info("Starting the update of all reports")
                for t in REPORT_TYPE.values():
                    t()
                return

            if arg.upper() in REPORT_TYPE.keys():
                logger.info(f"Starting the update of {arg} report")
                REPORT_TYPE[arg.upper()]()
            else:
                self.stdout.write(
                    self.style.ERROR(f"Unknown argument: {arg}"),
                )
