import logging
from pathlib import Path
from typing import Any
from typing import Optional

from django.core.management import BaseCommand
from django.core.management.base import CommandParser

from exporter.sqlite import make_export
from exporter.sqlite import make_export_script
from exporter.sqlite import runner
from exporter.sqlite import tasks

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
        parser.add_argument(
            "--dry-run",
            action="store_const",
            const=True,
            default=False,
        )
        parser.add_argument(
            "--make-only",
            action="store_const",
            const=True,
            default=False,
        )
        return super().add_arguments(parser)

    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        logger.info(f"Dumping tariff database to {options['destination']}")
        if options["dry_run"]:
            print(make_export_script(runner.Runner(options["destination"])).operations)
        elif options["make_only"]:
            make_export(options["destination"])
        else:
            tasks.export_and_upload_sqlite.delay()
