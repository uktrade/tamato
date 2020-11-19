import logging
import sys
from datetime import datetime
from typing import Iterator
from typing import List
from typing import Optional

import xlrd
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils.datastructures import OrderedSet
from psycopg2._range import DateTimeTZRange
from xlrd.sheet import Cell

from additional_codes.models import AdditionalCode, AdditionalCodeType
from commodities.models import GoodsNomenclature
from common.models import TrackedModel
from common.renderers import counter_generator
from common.validators import UpdateType
from geo_areas.models import GeographicalArea
from importer.management.commands.doc_importer import RowsImporter
from importer.management.commands.patterns import BREXIT, MeasureCreatingPatternWithExpression
from importer.management.commands.patterns import DualRowRunner
from importer.management.commands.patterns import MeasureEndingPattern
from importer.management.commands.patterns import OldMeasureRow
from importer.management.commands.utils import EnvelopeSerializer, cell_as_text, get_filtered_rows
from importer.management.commands.utils import MeasureTypeSlicer
from importer.management.commands.utils import NomenclatureTreeCollector
from importer.management.commands.utils import clean_item_id
from importer.management.commands.utils import col
from importer.management.commands.utils import parse_trade_remedies_duty_expression
from importer.management.commands.utils import split_groups
from measures.models import MeasureType
from regulations.models import Group
from regulations.models import Regulation
from regulations.validators import RoleType
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

logger = logging.getLogger(__name__)

BREXIT_TO_INFINITY = DateTimeTZRange(BREXIT, None)
MEASURE_TYPES = ['728', '277', '475', '711', '465', '707', '760', '714']
NEW_REGULATIONS = [
    (
        "The Iran (Sanctions) (Nuclear) (EU Exit) Regulations 2019; "
        "link https://www.legislation.gov.uk/uksi/2019/461/contents/made"
    ),
    (
        "The Democratic People’s Republic of Korea (Sanctions) (EU Exit) Regulations 2019 - "
        "link https://www.legislation.gov.uk/uksi/2019/411/contents/made"
    ),
    (
        "The Russia (Sanctions) (EU Exit) Regulations 2019 - "
        "link https://www.legislation.gov.uk/uksi/2019/855/contents/made"
    ),
    (
        "The Libya (Sanctions) (EU Exit) Regulations 2020 (not laid yet - will come into force on Exit day)"
    ),
    (
        "The Somalia (Sanctions) (EU Exit) Regulations 2020; Link - "
        "https://www.legislation.gov.uk/uksi/2020/642/contents/made"
    ),
    (
        "The Syria (Sanctions) (EU Exit) Regulations 2019 - link: "
        "https://www.legislation.gov.uk/uksi/2019/792/regulation/36/made"
    ),
]
NEW_REGULATION_PARAMS = {
    # Already defined in export controls
    NEW_REGULATIONS[0]: {
        'regulation_id': 'X1904610',
        'published_at': datetime(2019, 3, 5),
        'approved': True,
        'valid_between': BREXIT_TO_INFINITY,
        'information_text': (
            'The Iran (Sanctions) (Nuclear) (EU Exit) Regulations 2019|'
            'S.I. 2019/461|https://www.legislation.gov.uk/uksi/2019/461'
        )
    },
    # Already defined in export controls
    NEW_REGULATIONS[1]: {
        'regulation_id': 'X1904110',
        'published_at': datetime(2019, 3, 5),
        'approved': True,
        'valid_between': BREXIT_TO_INFINITY,
        'information_text': (
            'The Democratic People’s Republic of Korea (Sanctions) (EU Exit) Regulations 2019|'
            'S.I. 2019/411|https://www.legislation.gov.uk/uksi/2019/411'
        )
    },
    # Already defined in export controls
    NEW_REGULATIONS[2]: {
        'regulation_id': 'X1908550',
        'published_at': datetime(2019, 4, 10),
        'approved': True,
        'valid_between': BREXIT_TO_INFINITY,
        'information_text': (
            'The Russia (Sanctions) (EU Exit) Regulations 2019|'
            'S.I. 2019/855|https://www.legislation.gov.uk/uksi/2019/855'
        )
    },
    # Already defined in export controls
    NEW_REGULATIONS[3]: {
        'regulation_id': 'C2100110',
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': BREXIT_TO_INFINITY,
        'information_text': (
            'Libya Sanctions|S.I. 2021/11|https://www.legislation.gov.uk/uksi/2021/11'
        )
    },
    NEW_REGULATIONS[4]: {
        'regulation_id': 'X2006420',
        'published_at': datetime(2020, 6, 25),
        'approved': True,
        'valid_between': BREXIT_TO_INFINITY,
        'information_text': (
            'The Somalia (Sanctions) (EU Exit) Regulations 2020|'
            'S.I. 2020/642|https://www.legislation.gov.uk/uksi/2020/642'
        )
    },
    # Already defined in export controls
    NEW_REGULATIONS[5]: {
        'regulation_id': 'X1907920',
        'published_at': datetime(2019, 4, 3),
        'approved': True,
        'valid_between': BREXIT_TO_INFINITY,
        'information_text': (
            'The Syria (Sanctions) (EU Exit) Regulations 2019|'
            'S.I. 2019/792|https://www.legislation.gov.uk/uksi/2019/792'
        )
    },
}
REGULATION_MAPPING_OLD_NEW = {
    'R120267': NEW_REGULATIONS[0],
    'R172062': NEW_REGULATIONS[1],
    'R171548': NEW_REGULATIONS[1],
    'R180285': NEW_REGULATIONS[1],
    'R171509': NEW_REGULATIONS[1],
    'R171836': NEW_REGULATIONS[1],
    'R150936': NEW_REGULATIONS[1],
    'R170330': NEW_REGULATIONS[1],
    'D151764': NEW_REGULATIONS[2],
    'D140512': NEW_REGULATIONS[2],
    'R160044': NEW_REGULATIONS[3],
    'R120642': NEW_REGULATIONS[4],
    'R120036': NEW_REGULATIONS[5],
    'R131332': NEW_REGULATIONS[5],
    'R120168': NEW_REGULATIONS[5],
}


class NewRow:
    def __init__(self, new_row: List[Cell]) -> None:
        self.item_id = clean_item_id(new_row[col("A")])
        self.add_code = cell_as_text(new_row[col("B")]) if new_row[col("B")] else None
        self.legal_base = new_row[col("C")].value
        self.duty_rate = cell_as_text(new_row[col("D")])
        self.geo_area = GeographicalArea.objects.as_at(BREXIT).get(
            area_id=new_row[col("E")].value
        )
        self.measure_type = cell_as_text(new_row[col("F")])
        try:
            self.goods_nomenclature = GoodsNomenclature.objects.as_at(BREXIT).get(
                item_id=self.item_id, suffix="80"
            )
        except GoodsNomenclature.DoesNotExist:
            logger.warning(
                "Failed to find goods nomenclature %s/%s", self.item_id, "80"
            )
            self.goods_nomenclature = None


class ImportControlsImporter(RowsImporter):
    def setup(self) -> Iterator[TrackedModel]:
        self.measure_types = {}
        for measure_type in MEASURE_TYPES:
            self.measure_types[measure_type] = MeasureType.objects.get(sid=measure_type)
        self.measure_slicer = MeasureTypeSlicer[OldMeasureRow, NewRow](
            get_old_measure_type=lambda r: self.measure_types[r.measure_type],
            get_goods_nomenclature=lambda r: r.goods_nomenclature,
            default_measure_type=self.default_measure_type
        )
        self.old_rows = NomenclatureTreeCollector[List[OldMeasureRow]](BREXIT)
        self.new_rows = NomenclatureTreeCollector[NewRow](BREXIT)
        self.row_runner = DualRowRunner(self.old_rows, self.new_rows)
        self.brexit_to_infinity = DateTimeTZRange(BREXIT, None)
        self.generating_regulations = {}
        for i, regulation in enumerate(NEW_REGULATIONS):
            generating_regulation, _ = Regulation.objects.get_or_create(
                **NEW_REGULATION_PARAMS[regulation],
                role_type=RoleType.BASE,
                regulation_group=Group.objects.get(group_id="MLA"),
                workbasket=self.workbasket,
                update_type=UpdateType.CREATE,
            )
            self.generating_regulations[regulation] = generating_regulation
            # Only regulation 4 is not yet defined in export controls
            if self.first_run and regulation == NEW_REGULATIONS[4]:
                yield generating_regulation

        self.measure_ender = MeasureEndingPattern(
            workbasket=self.workbasket,
            measure_types=self.measure_types,
        )
        self.measure_creator = MeasureCreatingPatternWithExpression(
            duty_sentence_parser=None,
            generating_regulation=None,
            workbasket=self.workbasket,
            measure_sid_counter=self.counters["measure_sid_counter"],
            measure_condition_sid_counter=self.counters[
                "measure_condition_sid_counter"
            ],
        )

    def handle_row(
        self,
        new_row: Optional[NewRow],
        old_row: Optional[OldMeasureRow],
    ) -> Iterator[List[TrackedModel]]:
        for _ in self.row_runner.handle_rows(old_row, new_row):
            for transaction in self.flush():
                yield transaction

    def flush(self) -> Iterator[List[TrackedModel]]:
        # Send the old row to be end dated or removed
        old_sids = set()
        geo_areas = set()
        for cc, rows in self.old_rows.buffer():
            assert len(rows) >= 1
            for row in rows:
                assert (
                    row.measure_sid not in old_sids
                ), f"Measure appears more than once: {row.measure_sid}"
                old_sids.add(row.measure_sid)
                assert (
                    row.measure_type in self.measure_types
                ), f"{row.measure_type} not in {self.measure_types}"
                assert row.order_number is None
                geo_areas.add(row.geo_sid)
                assert len(geo_areas) == 1, "All geo_areas in buffer need to be same"
                #logger.debug("End-dating measure: %s", row.measure_sid)
                old_regulation_id_trimmed = row.regulation_id[:-1]
                new_regulation = REGULATION_MAPPING_OLD_NEW[old_regulation_id_trimmed]
                terminating_regulation = self.generating_regulations[new_regulation]
                yield list(
                    self.measure_ender.end_date_measure(
                        row,
                        terminating_regulation=terminating_regulation,
                    )
                )

        # Create measures either for the single measure type or a mix
        for (
            matched_old_rows,
            row,
            goods_nomenclature,
        ) in self.measure_slicer.sliced_new_rows(
                self.old_rows,
                self.new_rows,
        ):
            for transaction in self.make_new_measure(
                row, matched_old_rows, goods_nomenclature
            ):
                yield transaction

    def make_new_measure(
        self,
        new_row: NewRow,
        matched_old_rows: List[OldMeasureRow],
        goods_nomenclature: GoodsNomenclature,
    ) -> Iterator[List[TrackedModel]]:
        assert new_row is not None
        new_measure_type = self.measure_slicer.get_measure_type(
            matched_old_rows, goods_nomenclature
        )
        #footnote_list = [row.footnotes for row in matched_old_rows]
        #footnote_ids = list(
        #    set([footnote for sublist in footnote_list for footnote in sublist])
        #)
        #footnote_ids.sort()
        #footnotes = [
        #    Footnote.objects.as_at(BREXIT).get(
        #        footnote_id=f[2:], footnote_type__footnote_type_id=f[0:2]
        #    )
        #    for f in footnote_ids
        #]
        footnotes = []
        additional_code = None
        if new_row.add_code:
            additional_code = AdditionalCode.objects.get(
                type=AdditionalCodeType.objects.get(sid=new_row.add_code[0]),
                code=new_row.add_code[1:],
            )
        parsed_measure_expressions = parse_trade_remedies_duty_expression(
            new_row.duty_rate
        )
        yield list(
            self.measure_creator.create(
                geography=new_row.geo_area,
                goods_nomenclature=goods_nomenclature,
                new_measure_type=new_measure_type,
                validity_start=BREXIT,
                footnotes=footnotes,
                duty_condition_expressions=parsed_measure_expressions,
                additional_code=additional_code,
                generating_regulation=self.generating_regulations[new_row.legal_base]
            )
        )


class Command(BaseCommand):
    help = "Imports an import control format spreadsheet"

    def add_arguments(self, parser):
        parser.add_argument(
            "new-spreadsheet",
            help="The XLSX file to be parsed.",
            type=str,
        )
        parser.add_argument(
            "old-spreadsheet",
            help="The XLSX file containing existing measures to be parsed.",
            type=str,
        )
        parser.add_argument(
            "--new-measure-tabs",
            help="The tabs containing the new measures",
            action='append',
            default=[],
        )
        parser.add_argument(
            "--old-skip-rows",
            help="The number of rows from the spreadsheet to skip before importing data",
            type=int,
            default=0,
        )
        parser.add_argument(
            "--measure-sid",
            help="The SID value to use for the first new measure",
            type=int,
            default=200000000,
        )
        parser.add_argument(
            "--measure-condition-sid",
            help="The SID value to use for the first new measure condition",
            type=int,
            default=200000000,
        )
        parser.add_argument(
            "--transaction-id",
            help="The ID value to use for the first transaction",
            type=int,
            default=140,
        )
        parser.add_argument(
            "--envelope-id",
            help="The ID value to use for the envelope",
            type=int,
            default=1,
        )
        parser.add_argument(
            "--output", help="The filename to output to.", type=str, default="out.xml"
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

        new_workbook = xlrd.open_workbook(options["new-spreadsheet"])
        new_rows = []
        for tab in options["new_measure_tabs"]:
            new_rows += get_filtered_rows(
                sheet=new_workbook.sheet_by_name(tab),
                header_row_first_column='Goods code',
                columns=[
                    'Goods code',
                    'Add code',
                    'Legal base',
                    'Duty',
                    'Origin code',
                    'Meas. type code',
                ]
            )
        old_workbook = xlrd.open_workbook(options["old-spreadsheet"])
        old_worksheet = old_workbook.sheet_by_name("Sheet1")
        old_rows = old_worksheet.get_rows()
        for _ in range(options["old_skip_rows"]):
            next(old_rows)
        workbasket, _ = WorkBasket.objects.get_or_create(
            title=f"Import controls",
            author=author,
            status=WorkflowStatus.PUBLISHED,
        )

        with open(options["output"], mode="wb") as output:
            with EnvelopeSerializer(
                output,
                envelope_id=options["envelope_id"],
                transaction_counter=counter_generator(options["transaction_id"]),
                message_counter=counter_generator(start=1),
                max_envelope_size_in_mb=40,
            ) as env:
                measure_sid_counter = counter_generator(options["measure_sid"])
                measure_condition_sid_counter = counter_generator(
                    options["measure_condition_sid"]
                )

                # Split by additional code, origin code, measure_type groups
                new_groups = split_groups(new_rows, "A", ["B", "E", "F"])
                old_groups = split_groups(list(old_rows), "B", ["W", "L", "I"])
                logger.debug(new_groups.keys())
                logger.debug(old_groups.keys())

                group_ids = OrderedSet(
                    list(old_groups.keys()) + list(new_groups.keys())
                )
                for i, group_by_id in enumerate(group_ids):
                    new_group_rows = new_groups.get(group_by_id, [])
                    logger.debug(str([x[0] for x in new_group_rows]))
                    old_group_rows = old_groups.get(group_by_id, [])
                    logger.debug(str([x[1] for x in old_group_rows]))
                    logger.debug(
                        f"processing group {group_by_id}: {i + 1}/{len(group_ids)} with "
                        f"{len(new_group_rows)} new rows and {len(old_group_rows)} old rows"
                    )
                    importer = ImportControlsImporter(
                        workbasket,
                        env,
                        first_run=i == 0,
                        default_measure_type=MeasureType.objects.get(sid=group_by_id.split('|')[2]),
                    )
                    importer.counters["measure_sid_counter"] = measure_sid_counter
                    importer.counters[
                        "measure_condition_sid_counter"
                    ] = measure_condition_sid_counter
                    importer.import_sheets(
                        (NewRow(row) for row in new_group_rows),
                        (OldMeasureRow(row) for row in old_group_rows),
                    )
