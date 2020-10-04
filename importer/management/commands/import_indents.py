import logging
import sys
from datetime import datetime
from io import StringIO
from typing import Iterator
from typing import List
from typing import Optional

import xlrd
from django.contrib.auth.models import User
from django.core.management import BaseCommand
from xlrd.sheet import Cell

import settings
from commodities.models import GoodsNomenclature
from commodities.models import GoodsNomenclatureIndent
from common.models import TrackedModel
from common.validators import UpdateType
from importer.management.commands.doc_importer import BREXIT
from importer.management.commands.doc_importer import LONDON
from importer.management.commands.doc_importer import RowsImporter
from importer.management.commands.utils import EnvelopeSerializer
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

logger = logging.getLogger(__name__)


class Row:
    def __init__(self, row: List[Cell]) -> None:
        self.sid = int(row[1].value)
        self.commodity_code = str(row[4].value)
        self.suffix = str(row[5].value)
        self.indent = int(row[3].value)
        self.indent_sid = int(row[0].value)
        self.start_date = self.parse_date(row[2].value)
        # self.end_date = self.parse_date(row[6].value)
        # self.hs_level = int(row[7].value)
        # self.description = str(row[8].value)
        # self.parent_sid = int(row[9].value) if row[9].value != "" else None
        # self.parent_code = str(row[10].value) if row[10].value != "" else None
        # self.parent_suffix = str(row[11].value) if row[11].value != "" else None
        # self.parent_indent = int(row[12].value) if row[12].value != 0 else None
        # self.parent_indent_sid = int(row[13].value) if row[13].value != 0 else None

    def parse_date(self, value: str) -> Optional[datetime]:
        if value != "":
            return LONDON.localize(datetime.strptime(value, r"%Y-%m-%d"))
        else:
            return None


class IndentImporter(RowsImporter):
    def handle_row(
        self, new_row: Optional[Row], old_row: None
    ) -> Iterator[TrackedModel]:
        assert new_row

        indent = new_row.indent
        child = GoodsNomenclature.objects.get(sid=new_row.sid)
        item_id = child.item_id

        if (
            indent == 0 and item_id[2:] == "00000000"
        ):  # This is a root indent (i.e. a chapter heading)
            yield GoodsNomenclatureIndent.add_root(
                sid=new_row.indent_sid,
                indented_goods_nomenclature=child,
                valid_between=(new_row.start_date, None),
                workbasket=self.workbasket,
                update_type=UpdateType.CREATE,
            )
        else:
            # The indent is now too deep to use the item ID directly. Instead the code that is:
            #   - indent + 1
            #      - Due to the first two steps being given an indent of 0 in the TARIC, indents of offset by - 2.
            #   - Has a code that starts with the current path, omitting the last step.
            #   - Has a code that is greater than or equal to the current path
            #      - Some child codes have the same code as their parents.
            trimmed_id = item_id
            while trimmed_id.endswith("00"):
                trimmed_id = trimmed_id[:-2]
            trimmed_id = trimmed_id[:-2]

            parent_indent = indent + 1

            previously = (
                GoodsNomenclatureIndent.objects.filter(
                    indented_goods_nomenclature__sid=child.sid,
                )
                .order_by("valid_between")
                .reverse()
            )

            # We must detect any previous indent for this comm code
            # and end date it if this indent is overwriting it in the future
            if any(previously):
                previous = previously[0]
                logger.debug(
                    "Updating previous %s with start %s to have end %s",
                    previous,
                    previous.valid_between.lower,
                    new_row.start_date,
                )
                previous.valid_between = (
                    previous.valid_between.lower,
                    new_row.start_date,
                )
                previous.save()

            logger.debug(
                "Parent for %s: starts_with %s, <= %s, ind %s",
                new_row.commodity_code,
                trimmed_id,
                item_id,
                indent - 1,
            )

            parent = (
                GoodsNomenclatureIndent.objects.filter(
                    # indented_goods_nomenclature__item_id__startswith=trimmed_id,
                    indented_goods_nomenclature__item_id__lte=item_id,
                    indented_goods_nomenclature__valid_between__contains=(
                        new_row.start_date,
                        new_row.start_date,
                    ),
                    valid_between__contains=(new_row.start_date, new_row.start_date),
                    depth=parent_indent,
                )
                .order_by("indented_goods_nomenclature__item_id")
                .reverse()[0]
            )

            yield parent.add_child(
                sid=new_row.indent_sid,
                indented_goods_nomenclature=child,
                valid_between=(new_row.start_date, None),
                workbasket=self.workbasket,
                update_type=UpdateType.CREATE,
            )


class Command(BaseCommand):
    help = "Import a sheet of indents"

    def add_arguments(self, parser):
        parser.add_argument(
            "spreadsheet",
            help="The XLSX file to be parsed.",
            type=str,
        )
        parser.add_argument(
            "--sheet",
            help="The sheet name in the XLSX containing the data",
            type=str,
            default="Sheet1",
        )
        parser.add_argument(
            "--skip-rows",
            help="The number of rows from the spreadsheet to skip before importing data",
            type=int,
            default=0,
        )

    def handle(self, *args, **options):
        username = settings.DATA_IMPORT_USERNAME
        author = User.objects.get(username=username)

        workbasket, _ = WorkBasket.objects.get_or_create(
            title=f"Importing indents",
            author=author,
            status=WorkflowStatus.PUBLISHED,
        )

        workbook = xlrd.open_workbook(options["spreadsheet"])
        worksheet = workbook.sheet_by_name(options["sheet"])

        new_rows = worksheet.get_rows()
        for _ in range(options["skip_rows"]):
            next(new_rows)

        with EnvelopeSerializer(
            StringIO(),
            0,
        ) as env:
            importer = IndentImporter(workbasket, env)
            importer.import_sheets(
                (Row(row) for row in new_rows),
                iter([None]),
            )
