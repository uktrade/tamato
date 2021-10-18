import logging
from typing import Any
from typing import Optional

from django.core.management import BaseCommand
from django.core.management.base import CommandParser

from exporter.sqlite import tasks

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--immediately",
            action="store_const",
            help="Run the task in this process now rather than queueing it up",
            const=True,
            default=False,
        )
        return super().add_arguments(parser)

    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        logger.info(f"Triggering tariff database export to SQLite")

        go = tasks.export_and_upload_sqlite
        if not options["immediately"]:
            go = go.delay()
        go()
