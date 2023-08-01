import os
from typing import Any
from typing import Optional

from django.conf import settings
from django.core.management import BaseCommand
from django.core.management.base import CommandParser
from tabulate import tabulate

from importer.models import ImportBatch
from importer.models import ImporterChunkStatus
from workbaskets.models import WorkBasket


class Command(BaseCommand):
    help = "Inspect imports (ImportBatch) instances."

    SUBCOMMAND_LIST = "list"
    SUBCOMMAND_INSPECT = "inspect"

    ALL_SUBCOMMANDS = (
        SUBCOMMAND_LIST,
        SUBCOMMAND_INSPECT,
    )

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def add_arguments(self, parser: CommandParser) -> None:
        subparsers = parser.add_subparsers(
            dest="SUBCOMMAND",
            help=(f"Available subcommands are: {','.join(self.ALL_SUBCOMMANDS)}"),
        )

        # "list" subcommand to list imports.
        parser_list = subparsers.add_parser(
            self.SUBCOMMAND_LIST,
            help="List the most recent imports in reverse chronological order.",
        )
        parser_list.add_argument(
            "-n",
            "--number",
            help="Number of imports to list.",
            default=10,
            type=int,
        )

        # "inspect" subcommand to inspect specific imports.
        parser_inspect = subparsers.add_parser(
            self.SUBCOMMAND_INSPECT,
            help="Inspect an import.",
        )
        parser_inspect.add_argument(
            "IMPORT_BATCH_PK",
            help="The primary key of an ImportBatch instance.",
            type=int,
        )

    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        self.options = options

        # Default subcommand required state has poor error messages, so hadle
        # it here.
        if not self.options.get("SUBCOMMAND"):
            self.stdout.write(
                self.style.ERROR(
                    f"Error: {os.path.basename(__file__)} requires a SUBCOMMAND. "
                    f"Choose from one of: {', '.join(self.ALL_SUBCOMMANDS)}.",
                ),
            )
            exit(0)

        if self.options["SUBCOMMAND"] == self.SUBCOMMAND_LIST:
            self.handle_list()
        elif self.options["SUBCOMMAND"] == self.SUBCOMMAND_INSPECT:
            self.handle_inspect()

    def handle_list(self):
        number = self.options["number"]
        import_batch_qs = ImportBatch.objects.order_by("-created_at")[:number]

        headers = [
            "PK",
            "Name",
            "Status",
            "Chunk count",
            "Dependencies count",
            "WorkBasket",
        ]
        rows = []
        for ib in import_batch_qs:
            rows.append(
                [
                    ib.pk,
                    ib.name,
                    ib.status,
                    ib.chunks.all().count(),
                    ib.dependencies.all().count(),
                    self._workbasket_format(ib.workbasket),
                ],
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Showing a maximum of {number} most recent ImportBatch instances",
            ),
        )
        self.stdout.write(tabulate(rows, headers=headers))
        self.stdout.write()

    def handle_inspect(self):
        ib_pk = self.options["IMPORT_BATCH_PK"]
        try:
            ib = ImportBatch.objects.get(pk=ib_pk)
        except ImportBatch.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    f"No ImportBatch instance found with pk={ib_pk}",
                ),
            )
            exit(1)
        chunks_qs = ib.chunks.all()

        self.stdout.write(self.style.SUCCESS(f"ImportBatch details"))
        self.stdout.write(
            tabulate(
                [
                    ["PK:", ib.pk],
                    ["Name:", ib.name],
                    ["Author:", self._author_format(ib.author)],
                    ["Status:", ib.status],
                    ["Split job:", ib.split_job],
                    ["Chunk count:", chunks_qs.count()],
                    ["Dependencies count:", ib.dependencies.count()],
                    ["WorkBasket:", self._workbasket_format(ib.workbasket)],
                ],
                tablefmt="plain",
            ),
        )
        self.stdout.write()

        self.stdout.write(self.style.SUCCESS(f"Chunk details"))
        for c in chunks_qs:
            self.stdout.write(
                tabulate(
                    [
                        ["PK:", c.pk],
                        ["Status:", ImporterChunkStatus(c.status).name],
                        ["Chunk number:", c.chunk_number],
                        ["Record code:", c.record_code if c.record_code else "None"],
                        ["Chapter:", c.chapter if c.chapter else "None"],
                    ],
                    tablefmt="plain",
                ),
            )
            self.stdout.write()

    def _author_format(self, author: settings.AUTH_USER_MODEL) -> str:
        if not author:
            return "Unknown"
        return author.get_full_name() or author.email or author.username

    def _workbasket_format(self, workbasket: WorkBasket) -> str:
        if not workbasket:
            return "None"
        return (
            f"pk={workbasket.pk}, "
            f"status={workbasket.status}, "
            f"tracked_models.count={workbasket.tracked_models.count()}"
        )
