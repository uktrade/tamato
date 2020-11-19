import logging
import re
import sys
from datetime import timedelta
from typing import Iterator
from typing import List
from typing import Optional
from typing import Set
from typing import cast

import xlrd
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils.datastructures import OrderedSet
from psycopg2._range import DateTimeTZRange
from xlrd.sheet import Cell

from commodities.models import GoodsNomenclature
from common.models import TrackedModel
from common.renderers import counter_generator
from common.validators import UpdateType
from footnotes.models import Footnote, FootnoteType, FootnoteDescription
from footnotes.validators import ApplicationCode
from geo_areas.models import GeographicalArea
from importer.management.commands.doc_importer import RowsImporter
from importer.management.commands.patterns import BREXIT
from importer.management.commands.patterns import DualRowRunner
from importer.management.commands.patterns import LONDON
from importer.management.commands.patterns import MeasureCreatingPattern
from importer.management.commands.patterns import MeasureEndingPattern
from importer.management.commands.patterns import OldMeasureRow
from importer.management.commands.utils import EnvelopeSerializer
from importer.management.commands.utils import MeasureTypeSlicer
from importer.management.commands.utils import NomenclatureTreeCollector
from importer.management.commands.utils import SeasonalRateParser
from importer.management.commands.utils import clean_duty_sentence
from importer.management.commands.utils import clean_item_id
from importer.management.commands.utils import col
from importer.management.commands.utils import split_groups
from measures.models import MeasureType
from regulations.models import Group
from regulations.models import Regulation
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

logger = logging.getLogger(__name__)

FOOTNOTE_DETECTION_MAPPING = {
    'processing operations: dicing': 'DS001',
    'This suspension does not apply to any mixtures, preparations or products made up of different components containing these products.': 'TM861',
    'The measure is not allowed where processing is carried out by retail or catering undertakings.': 'TM851',
    'Authorised-Use customs supervision': 'EU001',
}
NEW_FOOTNOTE_DESCRIPTIONS = {
    'EU001': "Suspension of duties is subject to Authorised-Use customs supervision in accordance with Chapter 4 of The Customs (Special Procedures and Outward Processing) (EU Exit) Regulations 2018 (UK Statutory Instruments 2018 No. 1249)",
    'TM861': "This suspension does not apply to any mixtures, preparations or products made up of different components containing these products."
}

class TTRRow:
    def __init__(self, new_row: List[Cell]) -> None:
        assert new_row is not None
        self.item_id = clean_item_id(new_row[col("A")])
        self.suspension_rate = new_row[col("B")]
        self.footnote_ids = self._get_footnote_ids_from_notes(notes=str(new_row[col("C")].value))
        self.measure_type = '115' if 'EU001' in self.footnote_ids else '112'
        applies_to = re.findall(
            r'(?=(This suspension only applies to.*?(?:under this CN10 code.|under these CN10 codes.)))', str(new_row[col("C")].value).replace('Thi ', 'This ').replace('This suspensions', 'This suspension'), re.DOTALL
        )
        applies_to = re.sub(r'((\n)+(\s)*(\n)+)|\n', '<p/>', applies_to[0]).replace('•', '-').replace('Falling', 'falling') if applies_to else None
        self.applies_to = applies_to

        try:
            self.goods_nomenclature = GoodsNomenclature.objects.as_at(BREXIT).get(
                item_id=self.item_id, suffix="80"
            )
        except GoodsNomenclature.DoesNotExist as ex:
            logger.warning(
                "Failed to find goods nomenclature %s/%s", self.item_id, "80"
            )
            self.goods_nomenclature = None

    def _get_footnote_ids_from_notes(self, notes):
        footnotes = set()
        for text, footnote in FOOTNOTE_DETECTION_MAPPING.items():
            if text in notes:
                footnotes.add(footnote)
        if 'TM851' in footnotes and 'DS001' in footnotes:
            footnotes.remove('TM851')
        footnotes = list(footnotes)
        footnotes.sort()
        return footnotes


class SuspensionImporter(RowsImporter):
    def setup(self) -> Iterator[TrackedModel]:
        self.measure_types = {
            str(m.sid): m
            for m in [
                MeasureType.objects.get(sid="112"),
                MeasureType.objects.get(sid="115"),
            ]
        }
        self.measure_slicer = MeasureTypeSlicer[OldMeasureRow, NewRow](
            get_old_measure_type=lambda r: self.measure_types[r.measure_type],
            get_goods_nomenclature=lambda r: r.goods_nomenclature,
            default_measure_type=MeasureType.objects.get(sid="112"),
        )
        self.seasonal_rate_parser = SeasonalRateParser(BREXIT, LONDON)

        self.old_rows = NomenclatureTreeCollector[List[OldMeasureRow]](BREXIT)
        self.new_rows = NomenclatureTreeCollector[NewRow](BREXIT)
        self.row_runner = DualRowRunner(self.old_rows, self.new_rows)

        self.brexit_to_infinity = DateTimeTZRange(BREXIT, None)

        self.erga_omnes = GeographicalArea.objects.as_at(BREXIT).get(area_id="1011")
        self.suspensions_si = Regulation.objects.get(
            regulation_id="C2100003"
        )
        self.new_footnote_type = FootnoteType(
            footnote_type_id='DS',
            application_code=ApplicationCode.OTHER_MEASURES,
            description='Duty suspension',
            valid_between=self.brexit_to_infinity,
            workbasket=self.workbasket,
            update_type=UpdateType.CREATE,
        )
        yield self.new_footnote_type
        self.footnotes = {
            'TM851': Footnote.objects.get(
                footnote_id='851',
                footnote_type=FootnoteType.objects.get(footnote_type_id='TM'),
            ),
            'TM861': Footnote.objects.get(
                footnote_id='861',
                footnote_type=FootnoteType.objects.get(footnote_type_id='TM'),
            ),
            'TM026': Footnote.objects.get(
                footnote_id='026',
                footnote_type=FootnoteType.objects.get(footnote_type_id='TM'),
            ),
            'EU001': Footnote.objects.get(
                footnote_id='001',
                footnote_type=FootnoteType.objects.get(footnote_type_id='EU'),
            ),
        }
        for footnote, description in NEW_FOOTNOTE_DESCRIPTIONS.items():
            yield FootnoteDescription(
                description_period_sid=self.counters["footnote_description"](),
                description=description,
                valid_between=self.brexit_to_infinity,
                described_footnote=self.footnotes[footnote],
                workbasket=self.workbasket,
                update_type=UpdateType.CREATE,
            )
        new_footnote = Footnote(
            footnote_type=self.new_footnote_type,
            footnote_id=str(self.counters["new_footnote_id"]()).zfill(3),
            valid_between=self.brexit_to_infinity,
            workbasket=self.workbasket,
            update_type=UpdateType.CREATE,
        )
        new_footnote_description = FootnoteDescription(
            description_period_sid=self.counters["footnote_description"](),
            described_footnote=new_footnote,
            description="The measure is not allowed where processing is carried out by retail or catering undertakings.<p/>Subject to one or more of the following processing operations: dicing, filleting, production of flaps, cutting of frozen blocks, splitting of interleaved fillet blocks.<p/>For human consumption.",
            valid_between=self.brexit_to_infinity,
            workbasket=self.workbasket,
            update_type=UpdateType.CREATE,

        )
        yield [new_footnote, new_footnote_description]
        self.footnotes['DS001'] = new_footnote
        self.new_footnotes_created = {}

        self.measure_ender = MeasureEndingPattern(
            workbasket=self.workbasket,
            measure_types=self.measure_types,
        )

        self.measure_creator = MeasureCreatingPattern(
            generating_regulation=self.suspensions_si,
            workbasket=self.workbasket,
            duty_sentence_parser=self.duty_sentence_parser,
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
        # get new measure properties
        old_sids = set()
        measures_to_create = []
        for (
            matched_old_rows,
            new_row,
            goods_nomenclature,
        ) in self.measure_slicer.sliced_new_rows(self.old_rows, self.new_rows):
            new_footnote, new_footnote_description = None, None
            if new_row.applies_to:
                if new_row.applies_to in self.new_footnotes_created:
                    new_footnote = self.new_footnotes_created[new_row.applies_to]
                    logger.debug(f'Footnote {new_footnote} already created')
                else:
                    new_footnote = Footnote(
                        footnote_type=self.new_footnote_type,
                        footnote_id=str(self.counters["new_footnote_id"]()).zfill(3),
                        valid_between=self.brexit_to_infinity,
                        workbasket=self.workbasket,
                        update_type=UpdateType.CREATE,
                    )
                    self.new_footnotes_created[new_row.applies_to] = new_footnote
                    new_footnote_description = FootnoteDescription(
                        description_period_sid=self.counters["footnote_description"](),
                        described_footnote=new_footnote,
                        description=new_row.applies_to,
                        valid_between=self.brexit_to_infinity,
                        workbasket=self.workbasket,
                        update_type=UpdateType.CREATE,
                    )

            new_measure = self.get_new_measure(
                new_row, matched_old_rows, goods_nomenclature, new_footnote
            )

            # Check matched rows to keep or terminate
            match_found = False
            for row in matched_old_rows:
                if row.measure_sid in old_sids:
                    continue
                assert (
                    row.measure_type in self.measure_types
                ), f"{row.measure_type} not in {self.measure_types}"
                assert row.order_number is None
                assert row.geo_sid == self.erga_omnes.sid
                if row.goods_nomenclature_sid == new_measure['goods_nomenclature'].sid \
                    and row.geo_sid == new_measure['geography'].sid \
                    and clean_duty_sentence(row.duty_expression) == new_measure['duty_sentence'] \
                    and row.measure_type == new_measure['new_measure_type'].sid \
                    and row.measure_start_date == new_measure['validity_start'] \
                    and row.measure_end_date == new_measure['validity_end'] \
                    and set(row.footnotes) == set([str(f) for f in new_measure['footnotes']]):
                    logger.debug(f'Matching measure found for cc {row.measure_sid}')
                    match_found = True
                    old_sids.add(row.measure_sid)

            if not match_found:
                measures_to_create.append((new_measure, new_footnote, new_footnote_description))

        # Send the non-matching old row to be end dated or removed
        for cc, rows in self.old_rows.buffer():
            assert len(rows) >= 1
            for row in rows:
                if row.measure_sid in old_sids:
                    continue
                old_sids.add(row.measure_sid)
                assert (
                    row.measure_type in self.measure_types
                ), f"{row.measure_type} not in {self.measure_types}"
                assert row.order_number is None
                assert row.geo_sid == self.erga_omnes.sid
                logger.debug("End-dating remaining measure: %s", row.measure_sid)
                yield list(
                    self.measure_ender.end_date_measure(row, self.suspensions_si)
                )

        # Create new measures
        for measure, footnote, footnote_description in measures_to_create:
            if footnote and footnote_description:
                logger.debug(f'Creating footnote with {footnote}')
                yield [footnote, footnote_description]
            yield list(
                self.measure_creator.create(**measure)
            )

    def get_new_measure(
        self,
        new_row: NewRow,
        matched_old_rows: List[OldMeasureRow],
        goods_nomenclature: GoodsNomenclature,
        new_footnote: Footnote,
    ) -> Iterator[List[TrackedModel]]:
        assert new_row is not None
        old_measure_type = self.measure_slicer.get_measure_type(
            matched_old_rows, goods_nomenclature
        )
        old_footnote_list = [row.footnotes for row in matched_old_rows]
        old_footnote_ids = list(
            set([footnote for sublist in old_footnote_list for footnote in sublist])
        )
        footnotes = [
            self.footnotes[f] for f in new_row.footnote_ids
        ]
        if new_footnote:
            footnotes.append(new_footnote)
        footnotes.sort(key=lambda fn: str(fn))
        if matched_old_rows and set(old_footnote_ids) != set(new_row.footnote_ids):
            logger.debug(
                f'different footnotes for item {goods_nomenclature.item_id}: old {old_footnote_ids}, new {new_row.footnote_ids}'
            )
        if matched_old_rows and str(old_measure_type) != new_row.measure_type:
            logger.debug(
                f'different measure_types for item {goods_nomenclature.item_id}: old {old_measure_type}, new {new_row.measure_type}'
            )
        return {
            'duty_sentence': clean_duty_sentence(new_row.suspension_rate),
            'geography': self.erga_omnes,
            'goods_nomenclature': goods_nomenclature,
            'new_measure_type': self.measure_types[new_row.measure_type],
            'authorised_use': (new_row.measure_type == '115'),
            'validity_start': BREXIT,
            'validity_end': BREXIT.replace(year=2022) - timedelta(days=1),
            'footnotes': footnotes,
        }


class Command(BaseCommand):
    help = "Merge TTR and suspensions"

    def add_arguments(self, parser):
        parser.add_argument(
            "spreadsheet",
            help="The XLSX file containing measures to be parsed.",
            type=str,
        )
        parser.add_argument(
            "--measure-sid",
            help="The SID value to use for the first new measure",
            type=int,
        )
        parser.add_argument(
            "--measure-condition-sid",
            help="The SID value to use for the first new measure condition",
            type=int,
        )
        parser.add_argument(
            "--footnote-description-sid",
            help="The SID value to use for the first new footnote description",
            type=int,
        )
        parser.add_argument(
            "--transaction-id",
            help="The ID value to use for the first transaction",
            type=int,
        )
        parser.add_argument(
            "--envelope-id",
            help="The ID value to use for the envelope",
            type=int,
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
        old_workbook = xlrd.open_workbook(options["spreadsheet"])
        final_uk_suspensions = old_workbook.sheet_by_name("final_uk_suspensions")
        already_created_uk_suspensions = old_workbook.sheet_by_name("already_created_uk_suspensions")
        already_terminated_eu_suspensions = old_workbook.sheet_by_name("already_ended_eu_suspensions")
        final_uk_suspensions_rows = final_uk_suspensions.get_rows()
        already_created_uk_suspensions_rows = already_created_uk_suspensions.get_rows()
        already_terminated_eu_suspensions_rows = already_terminated_eu_suspensions.get_rows()
        for _ in range(1):
            next(final_uk_suspensions_rows)
            next(already_created_uk_suspensions_rows)
            next(already_terminated_eu_suspensions_rows)

        new_rows = [NewRow(row) for row in list(final_uk_suspensions_rows)]
        new_rows.sort(key=lambda row: row.item_id)
        old_rows = [
            OldMeasureRow(row) for row in list(
                already_created_uk_suspensions_rows
            ) + list(
                already_terminated_eu_suspensions_rows
            )
        ]
        old_rows.sort(key=lambda row: row.item_id)

        workbasket, _ = WorkBasket.objects.get_or_create(
            title=f"Autonomous Suspensions",
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
                importer = SuspensionImporter(
                    workbasket,
                    env,
                )
                importer.counters["measure_sid_counter"] = counter_generator(options["measure_sid"])
                importer.counters[
                    "measure_condition_sid_counter"
                ] = counter_generator(
                    options["measure_condition_sid"]
                )
                importer.counters[
                    "footnote_description"
                ] = counter_generator(
                    options["footnote_description_sid"]
                )
                importer.counters[
                    "new_footnote_id"
                ] = counter_generator(
                    1
                )
                importer.import_sheets(
                    new_rows,
                    old_rows,
                )

