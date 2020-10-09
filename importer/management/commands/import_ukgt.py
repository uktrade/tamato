import logging
from datetime import datetime
from datetime import timedelta
from typing import cast
from typing import Iterator
from typing import List
from typing import Optional

import xlrd
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from psycopg2._range import DateTimeTZRange
from xlrd.sheet import Cell

import settings
from additional_codes.models import AdditionalCode
from certificates.models import Certificate
from certificates.models import CertificateType
from commodities.models import GoodsNomenclature
from common.models import TrackedModel
from common.renderers import counter_generator
from common.validators import UpdateType
from geo_areas.models import GeographicalArea
from importer.management.commands.doc_importer import BREXIT
from importer.management.commands.doc_importer import LONDON
from importer.management.commands.doc_importer import RowsImporter
from importer.management.commands.patterns import OldMeasureRow
from importer.management.commands.utils import col
from importer.management.commands.utils import EnvelopeSerializer
from importer.management.commands.utils import maybe_min
from importer.management.commands.utils import MeasureTypeSlicer
from importer.management.commands.utils import NomenclatureTreeCollector
from importer.management.commands.utils import SeasonalRateParser
from measures.models import Measure
from measures.models import MeasureAction
from measures.models import MeasureCondition
from measures.models import MeasureConditionCode
from measures.models import MeasureType
from regulations.models import Group
from regulations.models import Regulation
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

logger = logging.getLogger(__name__)


class NewRow:
    def __init__(self, new_row: List[Cell]) -> None:
        assert new_row is not None
        self.additional_code = (
            str(int(new_row[col("C")].value)) if new_row[col("C")].value != "" else None
        )
        self.commodity_code = str(new_row[col("D")].value)
        self.cet_expression = new_row[col("G")]
        self.duty_expression = new_row[col("H")]
        self.ttr_expression = str(new_row[col("I")].value)
        self.ttr_less_than_ukgt = bool(new_row[col("J")].value)
        self.retained_trade_remedy = bool(new_row[col("K")].value)
        self.injury_margin = bool(new_row[col("L")].value)

        if len(self.commodity_code) == 8:
            self.item_id = self.commodity_code + "00"
        else:
            self.item_id = self.commodity_code

        try:
            self.goods_nomenclature = GoodsNomenclature.objects.as_at(BREXIT).get(
                item_id=self.item_id, suffix="80"
            )
        except GoodsNomenclature.DoesNotExist as ex:
            logger.warning("Failed to find goods nomenclature %s", self.item_id)
            self.goods_nomenclature = None


class UKGTImporter(RowsImporter):
    def setup(self) -> Iterator[TrackedModel]:
        third_country_duty = cast(MeasureType, MeasureType.objects.get(sid="103"))
        self.mfn_authorised_use = cast(MeasureType, MeasureType.objects.get(sid="105"))
        self.measure_types = {
            int(m.sid): m for m in [third_country_duty, self.mfn_authorised_use]
        }
        self.measure_slicer = MeasureTypeSlicer[OldMeasureRow, NewRow](
            get_old_measure_type=lambda r: self.measure_types[r.measure_type],
            get_goods_nomenclature=lambda r: r.goods_nomenclature,
        )
        self.seasonal_rate_parser = SeasonalRateParser(BREXIT, LONDON)
        self.measure_ending = MeasureEndingPattern(self.workbasket, self.measure_types)

        self.old_rows = NomenclatureTreeCollector[OldMeasureRow](
            lambda r: r.goods_nomenclature, BREXIT
        )
        self.new_rows = NomenclatureTreeCollector[NewRow](
            lambda r: r.goods_nomenclature, BREXIT
        )

        pharma_additional_code = cast(
            AdditionalCode, AdditionalCode.objects.get(type__sid="2", code="500")
        )
        other_additional_code = cast(
            AdditionalCode, AdditionalCode.objects.get(type__sid="2", code="501")
        )
        self.additional_codes = {
            str(a.type.sid + a.code): a
            for a in [pharma_additional_code, other_additional_code]
        }

        self.erga_omnes = GeographicalArea.objects.as_at(BREXIT).get(area_id="1011")
        self.brexit_to_infinity = DateTimeTZRange(BREXIT, None)
        self.mfn_regulation_group = Group.objects.get(group_id="DNC")

        self.ukgt_si, _ = Regulation.objects.get_or_create(
            regulation_id="C2100001",
            regulation_group=self.mfn_regulation_group,
            published_at=BREXIT,
            approved=False,
            valid_between=self.brexit_to_infinity,
            workbasket=self.workbasket,
            update_type=UpdateType.CREATE,
        )
        yield self.ukgt_si

        self.n990 = Certificate.objects.get(
            sid="990",
            certificate_type=CertificateType.objects.get(sid="N"),
        )

        self.presentation_of_certificate = MeasureConditionCode.objects.get(
            code="B",
        )

        self.apply_mentioned_duty = MeasureAction.objects.get(
            code="27",
        )

        self.subheading_not_allowed = MeasureAction.objects.get(
            code="08",
        )

    def clean_duty_sentence(self, cell: Cell) -> str:
        if cell.ctype == xlrd.XL_CELL_NUMBER:
            # This is a percentage value that Excel has
            # represented as a number.
            return f"{cell.value * 100}%"
        else:
            # All other values will apear as text.
            return cell.value

    def select_rate_on_trade_remedy(self, row: NewRow) -> Cell:
        """Where an injury margin applies the CET rate should
        be retained until the TRs have been reviewed."""
        if row.injury_margin:
            return row.cet_expression
        else:
            return row.duty_expression

    def handle_row(
        self,
        new_row: Optional[NewRow],
        old_row: Optional[OldMeasureRow],
    ) -> Iterator[List[TrackedModel]]:
        logger.debug(
            "Have old row: %s. Have new row: %s",
            old_row is not None,
            new_row is not None,
        )
        new_waiting = (
            new_row is not None
            and new_row.goods_nomenclature is not None
            and not self.new_rows.maybe_push(new_row)
        )
        if self.old_rows.subtree is None:
            self.old_rows.prefix = self.new_rows.prefix
            self.old_rows.subtree = self.new_rows.subtree
        old_waiting = (
            old_row is not None
            and old_row.goods_nomenclature is not None
            and not self.old_rows.maybe_push(old_row)
        )
        if self.new_rows.subtree is None:
            self.new_rows.prefix = self.old_rows.prefix
            self.new_rows.subtree = self.old_rows.subtree

        if old_waiting or new_waiting:
            # A row was rejected by the collector
            # The collector is full and we should process it
            logger.debug(
                f"Collector full with {len(self.old_rows.buffer)} old"
                f" and {len(self.new_rows.buffer)} new"
            )
            # We must always have an old row to detect the measure type
            assert len(self.old_rows.buffer) > 0

            # End date all the old rows in either case
            # We must do this first to maintain ME32
            for row in self.old_rows.buffer:
                for model in self.end_date_old_measure(row):
                    yield model

            # Create measures either for the single measure type or a mix
            for measure_type, row, gn in self.measure_slicer.sliced_new_rows(
                self.old_rows.buffer, self.new_rows.buffer
            ):
                for model in self.make_new_measure(row, measure_type, gn):
                    yield model

            self.old_rows.reset()
            self.new_rows.reset()
            for model in self.handle_row(
                new_row if new_waiting else None,
                old_row if old_waiting else None,
            ):
                yield model

        else:
            return iter([])

    def end_date_old_measure(self, old_row: OldRow) -> Iterator[TrackedModel]:
        if not old_row.inherited_measure:
            old_measure_type = self.measure_types[old_row.measure_type]
            assert old_row.geo_sid == self.erga_omnes.sid
            assert old_row.order_number is None

            # If the old measure starts after Brexit, we instead
            # need to delete it and it will never come into force
            # If it ends before Brexit, we don't need to do anything!
            starts_after_brexit = old_row.measure_start_date >= BREXIT
            ends_before_brexit = (
                old_row.measure_end_date and old_row.measure_end_date < BREXIT
            )

            regulation = Regulation.objects.get(
                role_type=old_row.regulation_role,
                regulation_id=old_row.regulation_id,
                regulation_group=self.mfn_regulation_group,
                valid_between=self.brexit_to_infinity,  # doesn't matter
                approved=True,
                update_type=UpdateType.CREATE,
                workbasket=self.workbasket,
            )

            if old_row.justification_regulation_id and starts_after_brexit:
                # We are going to delete the measure, but we still need the
                # regulation to be correct if it has already been end-dated
                assert old_row.measure_end_date
                justification_regulation = Regulation.objects.get(
                    role_type=old_row.regulation_role,
                    regulation_id=old_row.regulation_id,
                )
            elif not starts_after_brexit:
                # We are going to end-date the measure, and terminate it with
                # the UKGT SI.
                justification_regulation = self.ukgt_si
            else:
                # We are going to delete the measure but it has not been end-dated.
                assert old_row.measure_end_date is None
                justification_regulation = None

            if not ends_before_brexit:
                yield Measure(
                    sid=old_row.measure_sid,
                    measure_type=old_measure_type,
                    geographical_area=self.erga_omnes,
                    goods_nomenclature=old_row.goods_nomenclature,
                    additional_code=(
                        AdditionalCode.objects.get(sid=old_row.additional_code_sid)
                        if old_row.additional_code_sid
                        else None
                    ),
                    valid_between=DateTimeTZRange(
                        old_row.measure_start_date,
                        (
                            old_row.measure_end_date
                            if starts_after_brexit
                            else BREXIT - timedelta(days=1)
                        ),
                    ),
                    generating_regulation=regulation,
                    terminating_regulation=justification_regulation,
                    stopped=old_row.stopped,
                    reduction=old_row.reduction,
                    export_refund_nomenclature_sid=old_row.export_refund_sid,
                    update_type=(
                        UpdateType.DELETE if starts_after_brexit else UpdateType.UPDATE
                    ),
                    workbasket=self.workbasket,
                )

    def make_new_measure(
        self,
        new_row: NewRow,
        new_measure_type: MeasureType,
        goods_nomenclature: GoodsNomenclature,
    ) -> Iterator[TrackedModel]:
        assert new_row is not None

        duty_exp = self.clean_duty_sentence(self.select_rate_on_trade_remedy(new_row))
        for rate, start, end in self.seasonal_rate_parser.detect_seasonal_rates(
            duty_exp
        ):
            actual_end = maybe_min(end, goods_nomenclature.valid_between.upper)
            new_measure = Measure(
                sid=self.counters["measure_sid_counter"](),
                measure_type=new_measure_type,
                geographical_area=self.erga_omnes,
                goods_nomenclature=goods_nomenclature,
                valid_between=DateTimeTZRange(start, actual_end),
                generating_regulation=self.ukgt_si,
                terminating_regulation=(
                    self.ukgt_si if actual_end is not None else None
                ),
                additional_code=self.additional_codes[new_row.additional_code]
                if new_row.additional_code
                else None,
                update_type=UpdateType.CREATE,
                workbasket=self.workbasket,
            )
            yield new_measure

            if end != actual_end:
                logger.warning(
                    "Measure {} end date capped by {} end date: {:%Y-%m-%d}".format(
                        new_measure.sid, goods_nomenclature.item_id, actual_end
                    )
                )

            # If this is a measure under authorised use, we need to add
            # some measure conditions with the N990 certificate.
            if new_measure_type == self.mfn_authorised_use:
                yield MeasureCondition(
                    sid=self.counters["measure_condition_sid_counter"](),
                    dependent_measure=new_measure,
                    component_sequence_number=1,
                    condition_code=self.presentation_of_certificate,
                    required_certificate=self.n990,
                    action=self.apply_mentioned_duty,
                    update_type=UpdateType.CREATE,
                    workbasket=self.workbasket,
                )
                yield MeasureCondition(
                    sid=self.counters["measure_condition_sid_counter"](),
                    dependent_measure=new_measure,
                    component_sequence_number=2,
                    condition_code=self.presentation_of_certificate,
                    action=self.subheading_not_allowed,
                    update_type=UpdateType.CREATE,
                    workbasket=self.workbasket,
                )

            try:
                components = self.duty_sentence_parser.parse(rate)
                for component in components:
                    component.component_measure = new_measure
                    component.update_type = UpdateType.CREATE
                    component.workbasket = self.workbasket
                    yield component
            except RuntimeError as ex:
                logger.error(f"Explosion parsing {rate}")
                raise ex


class Command(BaseCommand):
    help = "Imports a UKGT format spreadsheet"

    def add_arguments(self, parser):
        parser.add_argument(
            "new-spreadsheet",
            help="The XLSX file to be parsed.",
            type=str,
        )
        parser.add_argument(
            "--new-sheet",
            help="The sheet name in the XLSX containing the data",
            type=str,
            default="Sheet1",
        )
        parser.add_argument(
            "--new-skip-rows",
            help="The number of rows from the spreadsheet to skip before importing data",
            type=int,
            default=0,
        )
        parser.add_argument(
            "old-spreadsheet",
            help="The XLSX file containing existing measures to be parsed.",
            type=str,
        )
        parser.add_argument(
            "--old-sheet",
            help="The sheet name in the XLSX containing the data",
            type=str,
            default="Sheet1",
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
            "--transaction-id",
            help="The ID value to use for the first transaction",
            type=int,
            default=140,
        )
        parser.add_argument(
            "--output", help="The filename to output to.", type=str, default="out.xml"
        )

    def handle(self, *args, **options):
        username = settings.DATA_IMPORT_USERNAME
        author = User.objects.get(username=username)

        new_workbook = xlrd.open_workbook(options["new-spreadsheet"])
        new_worksheet = new_workbook.sheet_by_name(options["new_sheet"])
        old_workbook = xlrd.open_workbook(options["old-spreadsheet"])
        old_worksheet = old_workbook.sheet_by_name(options["old_sheet"])

        workbasket, _ = WorkBasket.objects.get_or_create(
            title=f"UK Global Tariff",
            author=author,
            status=WorkflowStatus.PUBLISHED,
        )

        with open(options["output"], mode="w", encoding="UTF8") as output:
            with EnvelopeSerializer(
                output,
                200001,
                counter_generator(options["transaction_id"]),
            ) as env:

                logger.info(f"Importing from %s", new_worksheet.name)
                new_rows = new_worksheet.get_rows()
                old_rows = old_worksheet.get_rows()
                for _ in range(options["new_skip_rows"]):
                    next(new_rows)
                for _ in range(options["old_skip_rows"]):
                    next(old_rows)

                importer = UKGTImporter(workbasket, env)
                importer.counters["measure_sid_counter"] = counter_generator(
                    options["measure_sid"]
                )
                importer.counters["measure_condition_sid_counter"] = counter_generator(
                    options["measure_sid"]
                )

                importer.import_sheets(
                    (NewRow(row) for row in new_rows),
                    (OldMeasureRow(row) for row in old_rows),
                )
