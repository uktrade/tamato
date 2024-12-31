import logging

from django.core.management.base import BaseCommand

from open_data.tasks import update_all_tables

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "It deletes all the data in the reporting tables, and copy a fresh set of data"
        "from the tracked tables in the database."
    )

    def handle(self, *args, **options):
        logger.info(f"Starting the update of all the tables in the database")
        update_all_tables(True)

        self.stdout.write(
            self.style.SUCCESS("Successfully updated the reporting tables."),
        )
