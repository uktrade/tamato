from itertools import islice
from typing import Iterable
from typing import List
from typing import Optional

import xlrd
from django.core.management import BaseCommand
from django.db import transaction
from xlrd.book import Book
from xlrd.sheet import Cell

from importer.management.commands.utils import EnvelopeSerializer
from importer.management.commands.utils import get_author
from importer.management.commands.utils import id_argument
from importer.management.commands.utils import output_argument
from importer.management.commands.utils import write_summary
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus


class ImportCommand(BaseCommand):
    """A command that will set up import infrastructure and delegate to a child class
    to carry out an import. A workbasket will be created and the envelope
    serializer will output envelopes to the passed destination. Specify the `title`
    attribute on the child class to control the title of the resulting workbasket."""

    title = "Import run"

    def add_arguments(self, parser) -> None:
        id_argument(parser, "envelope")
        id_argument(parser, "transaction", 140)
        output_argument(parser)
        parser.add_argument(
            "--dry-run",
            help="Don't commit the import run",
            action="store_const",
            const=True,
            default=False,
        )

    def get_workbook(self, workbook: str) -> Book:
        """Load the workbook specified by a command-line option. The passed name
        must match a label given to `spreadsheet_argument`."""
        if workbook not in self.workbooks:
            infile = self.options[f"{workbook}-spreadsheet"]
            self.workbooks[workbook] = xlrd.open_workbook(infile)
        return self.workbooks[workbook]

    def get_sheet(
        self, workbook: str, name: str, skip: Optional[int] = None
    ) -> Iterable[List[Cell]]:
        """Load a stream of rows from the specified sheet. The passed workbook
        name must match a label given to `spreadsheet_argument`. A number of rows will
        be skipped either as specified on the command line or by the function arguments."""
        sheet = self.get_workbook(workbook).sheet_by_name(name)
        skip = skip or self.options[f"{workbook}_skip_rows"]
        return islice(sheet.get_rows(), skip, None)

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        self.workbooks = {}
        self.options = options

        author = get_author()
        workbasket, _ = WorkBasket.objects.get_or_create(
            title=self.title,
            author=author,
            status=WorkflowStatus.PUBLISHED,
        )

        with open(options["output"], mode="w", encoding="UTF8") as output:
            with EnvelopeSerializer(
                output,
                options["counters"]["envelope_id"](),
                options["counters"]["transaction_id"],
            ) as env:
                self.run(workbasket, env)

        if self.options["dry_run"]:
            transaction.set_rollback(True)

        write_summary(
            options["output"],
            workbasket.title,
            options["counters"],
            options["counters__original"],
        )

    def run(self, workbasket: WorkBasket, env: EnvelopeSerializer) -> None:
        """Carry out the import run. Implementations should override this to do
        the actual logic of parsing rows into objects and saving them."""
        pass
