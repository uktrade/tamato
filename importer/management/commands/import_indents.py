import logging
import os
import sys
from datetime import datetime
from typing import Iterator
from typing import List
from typing import Optional

import pytz
import xlrd
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import BaseCommand
from psycopg2._range import DateTimeTZRange
from xlrd.sheet import Cell

from commodities.import_handlers import GoodsNomenclatureIndentHandler
from commodities.models import GoodsNomenclature
from commodities.models import GoodsNomenclatureIndent
from commodities.models import GoodsNomenclatureIndentNode
from common.models import TrackedModel
from common.validators import UpdateType
from importer.management.commands.doc_importer import RowsImporter
from importer.management.commands.utils import EnvelopeSerializer
from importer.management.commands.utils import maybe_min
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

logger = logging.getLogger(__name__)


class Row:
    def __init__(self, row: List[Cell]) -> None:
        self.sid = int(row[1].value)
        self.commodity_code = str(row[5].value)
        self.suffix = str(row[6].value)
        self.indent = int(row[4].value)
        self.indent_sid = int(row[0].value)
        self.start_date = self.parse_date(row[2].value)
        self.end_date = self.parse_date(row[3].value)

    def parse_date(self, value: str) -> Optional[datetime]:
        if value != "":
            return pytz.utc.localize(datetime.strptime(value, r"%Y-%m-%d"))
        else:
            return None


class IndentImporter(RowsImporter):
    """Import indents from a spreadsheet dump of existing indents.
    The spreadsheed output should include a column for the end date of the indent.
    This can be calculated by subtracting 1 from the start date of the next indent
    for the same SID. A la:

        MAX(goods_nomenclature_indents.validity_start_date) OVER (
            PARTITION BY goods_nomenclature_indents.goods_nomenclature_sid
            ORDER BY goods_nomenclature_indents.validity_end_date ASC
            ROWS BETWEEN CURRENT ROW AND 1 FOLLOWING
        ) AS validity_end_date

    This importer will then, for each indent, walk forward from the start date
    to the end date and discover all of the parents this indent has had for it's lifetime,
    and create one child node with an appropriate validity range under that parent.
    So, if the parent indent ends before the child indent, the next parent will be found
    and a node created under that new parent from the end date of the old parent.

    Note that indents will not have end dates in this spreadsheet if the indented
    commodity code is ended, so the end date of the goods nomenclature must be taken into
    account too.

    The end result is a set of GoodsNomenclatureIndent models with correct parent codes and
    validity ranges that represent the time that code was the parent, such that a call to

        GoodsNomenclature.get(…).indents.as_at(…).get()

    will return the correct indent and the correct parent code at that time."""

    def handle_row(
        self, new_row: Optional[Row], old_row: None
    ) -> Iterator[List[TrackedModel]]:
        assert new_row

        indent = new_row.indent
        child = GoodsNomenclature.objects.get(sid=new_row.sid)
        item_id = child.item_id
        suffix = child.suffix

        indent_model = GoodsNomenclatureIndent(
            sid=new_row.indent_sid,
            indented_goods_nomenclature=child,
            indent=max(indent, 0),
            valid_between=DateTimeTZRange(new_row.start_date, new_row.end_date),
            workbasket=self.workbasket,
            update_type=UpdateType.CREATE,
        )
        indent_model.save()
        yield [indent_model]

        if (
            indent == -1 and item_id[2:] == "00000000"
        ):  # This is a root indent (i.e. a chapter heading)
            GoodsNomenclatureIndentNode.add_root(
                indent=indent_model,
                valid_between=DateTimeTZRange(new_row.start_date, new_row.end_date),
            )
        else:
            # The indent is now too deep to use the item ID directly. Instead the code that is:
            #   - indent + 1
            #      - Due to the first two steps being given an indent of 0 in the TARIC, indents of offset by - 2.
            #   - Has a code that starts with the current path, omitting the last step.
            #   - Has a code that is greater than or equal to the current path
            #      - Some child codes have the same code as their parents.
            parent_depth = indent + 1

            # Very high up in places like chapter 29 we get another
            # level of headings that also have indent zero, so the
            # relationship between depth and indent is actually -3
            # Except, for whatever reason, in frankenchapter 99 where
            # there is an extra heading but the indents are correct
            # We can detect this by looking for phantom lines at the
            # four digit level:
            chapter_heading = item_id[:2]
            extra_headings = (
                any(
                    GoodsNomenclature.objects.filter(
                        item_id__startswith=chapter_heading,
                        item_id__endswith="000000",
                    ).exclude(suffix="80")
                )
                and chapter_heading != "99"
            )

            # So we need to add extra depth if we are now below an extra heading
            # which will be true if our last 6 digits are not zero or if we are
            # on a real heading (last 6 digits zero and suffix 80)
            if extra_headings and (
                item_id[4:] != "000000" or (item_id[4:] == "000000" and suffix == "80")
            ):
                parent_depth += 1

            # This is the time range that needs to be covered by
            # the indents that we create. We will subtract from
            # this range as we discover the correct parents.
            start_date = new_row.start_date
            end_date = maybe_min(
                new_row.end_date,
                child.valid_between.upper,
            )

            # Keep looking for parents whilst we have remaining time.
            # The end condition is that the start date is now equal to the end date,
            # or the end date of the indented code, or there is no end date so both are None.
            while start_date and ((start_date < end_date) if end_date else True):
                logger.debug(
                    "Looking for parent for %s(%s) between time %s and %s",
                    child.item_id,
                    child.suffix,
                    start_date,
                    end_date,
                )

                defn = (
                    new_row.indent_sid,
                    start_date.year,
                    start_date.month,
                    start_date.day,
                )

                if defn in GoodsNomenclatureIndentHandler.overrides:
                    next_indent = GoodsNomenclatureIndent.objects.get(
                        sid=GoodsNomenclatureIndentHandler.overrides[defn]
                    )
                    next_parent = next_indent.nodes.filter(
                        valid_between__contains=start_date
                    ).get()
                    logger.info("Using manual override for indent %s", defn)
                else:
                    next_parent = (
                        GoodsNomenclatureIndentNode.objects.filter(
                            indent__indented_goods_nomenclature__item_id__lte=item_id,
                            indent__indented_goods_nomenclature__item_id__startswith=chapter_heading,
                            indent__indented_goods_nomenclature__valid_between__contains=start_date,
                            indent__valid_between__contains=start_date,
                            valid_between__contains=start_date,
                            depth=parent_depth,
                        )
                        .order_by("-indent__indented_goods_nomenclature__item_id")
                        .first()
                    )

                if not next_parent:
                    raise Exception(
                        f"Parent at depth {parent_depth} not found for {item_id} (sid {child.sid}) for date {start_date}"
                    )

                indent_start = start_date
                indent_end = maybe_min(
                    next_parent.valid_between.upper,
                    next_parent.indent.valid_between.upper,
                    next_parent.indent.indented_goods_nomenclature.valid_between.upper,
                    end_date,
                )

                assert indent_end is None or indent_start <= indent_end

                logger.debug(
                    "%s(%s) is parent of %s(%s) between %s and %s",
                    next_parent.indent.indented_goods_nomenclature.item_id,
                    next_parent.indent.indented_goods_nomenclature.suffix,
                    child.item_id,
                    child.suffix,
                    indent_start,
                    indent_end,
                )

                next_parent.add_child(
                    indent=indent_model,
                    valid_between=DateTimeTZRange(indent_start, indent_end),
                )

                start_date = indent_end


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
        try:
            author = User.objects.get(username=username)
        except User.DoesNotExist:
            sys.exit(
                f"Author does not exist, create user '{username}'"
                " or edit settings.DATA_IMPORT_USERNAME"
            )

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
            open(os.devnull, "w"),
            0,
        ) as env:
            importer = IndentImporter(workbasket, env)
            importer.import_sheets(
                (Row(row) for row in new_rows),
                iter([None]),
            )
