import logging
from pathlib import Path
from typing import Any
from typing import Optional

from django.core.management import BaseCommand
from django.core.management.base import CommandParser

from exporter.sqlite import make_export

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "destination",
            nargs="?",
            type=Path,
            default=Path("tariff.db"),
            help="A path to write an SQLite database to",
        )
        return super().add_arguments(parser)

    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        logger.info(f"Dumping tariff database to {options['destination']}")
        make_export(options["destination"])
