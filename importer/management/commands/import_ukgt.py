import logging
import re
from datetime import datetime
from datetime import timedelta
from typing import Dict
from typing import Iterator
from typing import List
from typing import Optional
from typing import Union

import django.db
import pytz
import settings
import xlrd
from certificates.models import Certificate
from certificates.models import CertificateType
from commodities.models import GoodsNomenclature
from common.models import TrackedModel
from common.renderers import counter_generator
from common.serializers import TrackedModelSerializer
from common.validators import UpdateType
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.template.loader import render_to_string
from geo_areas.models import GeographicalArea
from importer.duty_sentence_parser import DutySentenceParser
from measures.models import DutyExpression
from measures.models import Measure
from measures.models import MeasureAction
from measures.models import MeasureCondition
from measures.models import MeasureConditionCode
from measures.models import Measurement
from measures.models import MeasureType
from measures.models import MonetaryUnit
from psycopg2._range import DateTimeTZRange
from regulations.models import Group
from regulations.models import Regulation
from workbaskets.models import Transaction
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus
from xlrd.sheet import Cell

logger = logging.getLogger(__name__)

LONDON = pytz.timezone("Europe/London")
BREXIT = LONDON.localize(datetime(2021, 1, 1))

TRADE_REMEDY_RATE = re.compile(r"^\(([\d\.]+%)\)")
SEASONAL_RATE = re.compile(r"([\d\.]+%) \((\d\d [A-Z]{3}) - (\d\d [A-Z]{3})\)")


class NewRow:
    def __init__(self, new_row: List[Cell]) -> None:
        assert new_row is not None
        self.level = "CN8"  # new_row[0].value
        self.comm_code = new_row[3].value  # new_row[1].value
        self.item_id = self.comm_code if self.level == "CN10" else self.comm_code + "00"
        self.duty_expression = new_row[13]  # [4]


class OldRow:
    def __init__(self, old_row: List[Cell]) -> None:
        assert old_row is not None
        self.goods_nomenclature_sid = old_row[0].value
        self.item_id = old_row[1].value
        self.inherited_measure = old_row[8].value
        self.measure_sid = old_row[9].value
        self.measure_type = int(old_row[10].value)
        self.geo_sid = old_row[15].value
        self.measure_start_date = self.parse_date(old_row[18].value)
        self.measure_end_date = self.parse_date(old_row[19].value)
        self.regulation_role = int(old_row[20].value)
        self.regulation_id = old_row[21].value

    def parse_date(self, value: str) -> Optional[datetime]:
        if value != "":
            return LONDON.localize(datetime.strptime(value, r"%Y-%m-%d"))
        else:
            return None


def earliest(*dates: Optional[datetime]) -> Optional[datetime]:
    present = [d for d in dates if d is not None]
    if any(present):
        return min(present)
    else:
        return None


class RowCollector:
    # If the row is an 8 digit code, consume rows for as long
    # as the 10 digit old row matches the 8 digit prefix

    def __init__(self) -> None:
        self.old_buffer = []
        self.new_buffer = []
        self.prefix = ""

    def maybe_append(self, buffer: List, row: Union[OldRow, NewRow]) -> bool:
        if self.prefix == "":
            self.prefix = row.item_id[0:8]

        if row.item_id.startswith(self.prefix):
            buffer.append(row)
            return True
        else:
            return False

    def push_new(self, new_row: NewRow) -> bool:
        return self.maybe_append(self.new_buffer, new_row)

    def push_old(self, old_row: OldRow) -> bool:
        return self.maybe_append(self.old_buffer, old_row)


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

    def setup(self, workbasket: WorkBasket, options: Dict) -> Iterator[TrackedModel]:
        self.third_country_duty = MeasureType.objects.get(sid="103")
        self.non_pref_under_end_use = MeasureType.objects.get(sid="105")
        self.erga_omnes = GeographicalArea.objects.as_at(BREXIT).get(area_id="1011")
        self.brexit_to_infinity = DateTimeTZRange(BREXIT, None)
        self.mfn_regulation_group = Group.objects.get(group_id="DNC")
        self.measure_sid_counter = counter_generator(options["measure_sid"])
        self.measure_condition_sid_counter = counter_generator(options["measure_sid"])
        self.transaction_counter = counter_generator(options["transaction_id"])

        self.ukgt_si, _ = Regulation.objects.get_or_create(
            regulation_id="C2100001",
            regulation_group=self.mfn_regulation_group,
            published_at=BREXIT,
            approved=False,
            valid_between=self.brexit_to_infinity,
            workbasket=workbasket,
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
        elif TRADE_REMEDY_RATE.match(cell.value):
            # A trade remedy still applies, so we need
            # to keep the bracketed rate
            return TRADE_REMEDY_RATE.match(cell.value).group(1)
        else:
            # All other values will apear as text.
            return cell.value

    def detect_seasonal_rates(self, duty_exp: str) -> Iterator:
        logger.debug("Detecting seasonal rates in %s", duty_exp)
        if SEASONAL_RATE.search(duty_exp):
            for match in SEASONAL_RATE.finditer(duty_exp):
                rate, start, end = match.groups()
                validity_start = LONDON.localize(datetime.strptime(start, r"%d %b"))
                validity_end = LONDON.localize(datetime.strptime(end, r"%d %b"))
                if validity_start.month > validity_end.month:
                    # This straddles a year boundary so
                    # we need to make one measure for BREXIT to end
                    # and then another for start to BREXIT+1
                    yield (rate, BREXIT, validity_end.replace(year=2021))
                    yield (
                        rate,
                        validity_start.replace(year=2021),
                        BREXIT.replace(year=2022) - timedelta(days=1),
                    )
                else:
                    # Both months are in one year, hence make them 2021
                    yield (
                        rate,
                        validity_start.replace(year=2021),
                        validity_end.replace(year=2021),
                    )
        else:
            # Non-seasonal rate!
            yield (duty_exp, BREXIT, None)

    def compare_rows(self, new_row: Optional[NewRow], old_row: Optional[OldRow]) -> int:
        if new_row is None:
            return -1
        if old_row is None:
            return 1

        logger.debug("Comparing old %s and new %s", old_row.item_id, new_row.item_id)
        if old_row.item_id < new_row.item_id:
            return -1
        elif old_row.item_id > new_row.item_id:
            return 1
        else:
            return 0

    def handle_row(
        self,
        workbasket: WorkBasket,
        new_row: Optional[NewRow],
        old_row: Optional[OldRow],
    ) -> Iterator[TrackedModel]:
        logger.debug(
            "Have old row: %s. Have new row: %s",
            old_row is not None,
            new_row is not None,
        )
        old_waiting = old_row is not None and not self.row_collector.push_old(old_row)
        new_waiting = new_row is not None and not self.row_collector.push_new(new_row)
        if old_waiting or new_waiting:
            # A row was rejected by the collector
            # The collector is full and we should process it
            logger.debug(
                f"Collector full with {len(self.row_collector.old_buffer)} old"
                f" and {len(self.row_collector.new_buffer)} new"
            )
            # Detect which measure types are in the old rows and if both
            # measure types are present, generate new measures for each old row
            # If only one measure type is present, generate one measure for it
            # We may have duplicate entries due to Entry Price System but
            # we only want one new measure per item id
            plain = set(
                str(r.item_id)
                for r in self.row_collector.old_buffer
                if r.measure_type == 103
            )
            authd = set(
                str(r.item_id)
                for r in self.row_collector.old_buffer
                if r.measure_type == 105
            )
            if len(plain) == 0 or len(authd) == 0:
                # All the old rows are of a single measure type
                # Just create the new rows as desired
                new_measure_type = (
                    self.non_pref_under_end_use
                    if len(authd) > 0
                    else self.third_country_duty
                )
                for row in self.row_collector.new_buffer:
                    for model in self.make_new_measure(
                        workbasket, row, new_measure_type, row.item_id
                    ):
                        yield model
            else:
                # There is a split of measure types across the old rows
                # Mirror the split in the new measures by using the old item ids
                parent_new = next(
                    (r for r in self.row_collector.new_buffer if len(r.comm_code) == 8),
                    None,
                )
                if parent_new is not None:
                    for old_plain in plain:
                        matching_new = next(
                            (
                                r
                                for r in self.row_collector.new_buffer
                                if r.item_id == old_plain
                            ),
                            parent_new,
                        )
                        for model in self.make_new_measure(
                            workbasket, matching_new, self.third_country_duty, old_plain
                        ):
                            yield model
                    for old_authd in authd:
                        matching_new = next(
                            (
                                r
                                for r in self.row_collector.new_buffer
                                if r.item_id == old_authd
                            ),
                            parent_new,
                        )
                        for model in self.make_new_measure(
                            workbasket,
                            matching_new,
                            self.non_pref_under_end_use,
                            old_authd,
                        ):
                            yield model
                else:
                    assert len(self.rows_collector.new_buffer) == 0

            # End date all the old rows in either case
            for row in self.row_collector.old_buffer:
                for model in self.end_date_old_measure(workbasket, row):
                    yield model

            self.row_collector = RowCollector()
            for model in self.handle_row(
                workbasket,
                new_row if new_waiting else None,
                old_row if old_waiting else None,
            ):
                yield model

        else:
            return iter([])

    def end_date_old_measure(
        self, workbasket: WorkBasket, old_row: OldRow
    ) -> Iterator[TrackedModel]:
        if not old_row.inherited_measure:
            goods_nomenclature = GoodsNomenclature.objects.get(
                sid=old_row.goods_nomenclature_sid
            )

            old_measure_type = (
                self.third_country_duty
                if old_row.measure_type == 103
                else self.non_pref_under_end_use
            )

            assert old_row.geo_sid == self.erga_omnes.sid
            regulation, _ = Regulation.objects.get_or_create(
                role_type=old_row.regulation_role,
                regulation_id=old_row.regulation_id,
                regulation_group=self.mfn_regulation_group,
                valid_between=self.brexit_to_infinity,  # doesn't matter
                approved=True,
                update_type=UpdateType.CREATE,
                workbasket=workbasket,
            )
            regulation.save()

            # If the old measure starts after Brexit, we instead
            # need to delete it and it will never come into force
            starts_after_brexit = old_row.measure_start_date >= BREXIT
            yield Measure(
                sid=old_row.measure_sid,
                measure_type=old_measure_type,
                geographical_area=self.erga_omnes,
                goods_nomenclature=goods_nomenclature,
                valid_between=DateTimeTZRange(
                    old_row.measure_start_date,
                    (
                        old_row.measure_end_date
                        if starts_after_brexit
                        else BREXIT - timedelta(days=1)
                    ),
                ),
                generating_regulation=regulation,
                terminating_regulation=(None if starts_after_brexit else self.ukgt_si),
                update_type=(
                    UpdateType.DELETE if starts_after_brexit else UpdateType.UPDATE
                ),
                workbasket=workbasket,
            )

    def make_new_measure(
        self,
        workbasket: WorkBasket,
        new_row: NewRow,
        new_measure_type: MeasureType,
        item_id: str,
    ) -> Iterator[TrackedModel]:
        assert new_row is not None
        try:
            goods_nomenclature = GoodsNomenclature.objects.as_at(BREXIT).get(
                item_id=item_id,
                suffix="80",
            )
        except GoodsNomenclature.DoesNotExist:
            logger.error(
                "Failed to make measure for %s as goods code does not exist", item_id
            )
            return

        ukgt = self.clean_duty_sentence(new_row.duty_expression)
        for rate, start, end in self.detect_seasonal_rates(ukgt):
            actual_end = earliest(end, goods_nomenclature.valid_between.upper)
            new_measure = Measure(
                sid=self.measure_sid_counter(),
                measure_type=new_measure_type,
                geographical_area=self.erga_omnes,
                goods_nomenclature=goods_nomenclature,
                valid_between=DateTimeTZRange(start, actual_end),
                generating_regulation=self.ukgt_si,
                terminating_regulation=(
                    self.ukgt_si if actual_end is not None else None
                ),
                update_type=UpdateType.CREATE,
                workbasket=workbasket,
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
            if new_measure_type == self.non_pref_under_end_use:
                yield MeasureCondition(
                    sid=self.measure_condition_sid_counter(),
                    dependent_measure=new_measure,
                    component_sequence_number=1,
                    condition_code=self.presentation_of_certificate,
                    required_certificate=self.n990,
                    action=self.apply_mentioned_duty,
                    update_type=UpdateType.CREATE,
                    workbasket=workbasket,
                )
                yield MeasureCondition(
                    sid=self.measure_condition_sid_counter(),
                    dependent_measure=new_measure,
                    component_sequence_number=2,
                    condition_code=self.presentation_of_certificate,
                    action=self.subheading_not_allowed,
                    update_type=UpdateType.CREATE,
                    workbasket=workbasket,
                )

            try:
                components = self.duty_sentence_parser.parse(rate)
                for component in components:
                    component.component_measure = new_measure
                    component.update_type = UpdateType.CREATE
                    component.workbasket = workbasket
                    yield component
            except RuntimeError as ex:
                logger.error(f"Explosion parsing {rate}")
                raise ex

    def handle(self, *args, **options):
        duty_expressions = (
            DutyExpression.objects.as_at(BREXIT)
            .order_by("sid")
            .exclude(
                sid__exact=37  # 37 is literal nothing, which will match all strings
            )
        )
        monetary_units = MonetaryUnit.objects.as_at(BREXIT)
        permitted_measurements = (
            Measurement.objects.as_at(BREXIT)
            .exclude(measurement_unit__abbreviation__exact="")
            .exclude(
                measurement_unit_qualifier__abbreviation__exact="",
            )
        )

        self.duty_sentence_parser = DutySentenceParser(
            duty_expressions, monetary_units, permitted_measurements
        )

        new_workbook = xlrd.open_workbook(options["new-spreadsheet"])
        new_worksheet = new_workbook.sheet_by_name(options["new_sheet"])
        old_workbook = xlrd.open_workbook(options["old-spreadsheet"])
        old_worksheet = old_workbook.sheet_by_name(options["old_sheet"])

        workbasket_status = WorkflowStatus.PUBLISHED
        username = settings.DATA_IMPORT_USERNAME
        author = User.objects.get(username=username)

        with django.db.transaction.atomic():
            logger.info(f"Importing from %s", options["new-spreadsheet"])
            workbasket, _ = WorkBasket.objects.get_or_create(
                title=f"UK Global Tariff",
                author=author,
                status=workbasket_status,
            )

            with open(options["output"], mode="w", encoding="UTF8") as output:
                output.write(
                    render_to_string(
                        template_name="common/taric/start_envelope.xml",
                        context={"envelope_id": 200001},
                    )
                )

                self.transaction_counter = counter_generator()
                self.message_counter = counter_generator()
                self.serializer = TrackedModelSerializer(context={"format": "xml"})

                setup_models = []
                for model in self.setup(workbasket, options):
                    model.full_clean()
                    model.save()
                    setup_models.append(model)
                output.write(self.render_transaction(workbasket, setup_models))

                new_proceed = old_proceed = True
                new_row_generator = enumerate(new_worksheet.get_rows())
                old_row_generator = enumerate(old_worksheet.get_rows())
                new_row_number, new_row = next(new_row_generator)
                old_row_number, old_row = next(old_row_generator)
                self.row_collector = RowCollector()

                while new_proceed or old_proceed:
                    handle_args = [None, None]  # for skipping
                    if old_row_number < options["old_skip_rows"]:
                        handle_args[1] = True
                    if new_row_number < options["new_skip_rows"]:
                        handle_args[0] = True

                    if handle_args == [None, None]:
                        try:
                            new = NewRow(new_row) if new_row else None
                            old = OldRow(old_row) if old_row else None
                            compare = self.compare_rows(new, old)
                            if compare < 0:
                                # Old row comes before new row
                                # Hence it is a row we are not replacing
                                handle_args = [None, old]
                            elif compare > 0:
                                # Old row comes after new row
                                # Hence new row is completely new
                                handle_args = [new, None]
                            else:  # compare == 0
                                # Rows compared equal
                                # Hence new row is replacing the old row
                                handle_args = [new, old]

                            tracked_models = []
                            for model in self.handle_row(workbasket, *handle_args):
                                # model.clean_fields()
                                # model.save()
                                logger.debug(model)
                                tracked_models.append(model)

                            if any(tracked_models):
                                output.write(
                                    self.render_transaction(workbasket, tracked_models)
                                )

                            if old_row_number % 500 == 0:
                                logger.info("Progress: at row %d", old_row_number)
                        except Exception as ex:
                            logger.error(
                                f"Explosion whilst handling {new_row} or {old_row}"
                            )
                            raise ex

                    try:
                        if handle_args[1] is not None:
                            old_row_number, old_row = next(old_row_generator)
                    except StopIteration:
                        old_proceed = False
                        old_row = None

                    try:
                        if handle_args[0] is not None:
                            new_row_number, new_row = next(new_row_generator)
                    except StopIteration:
                        new_proceed = False
                        new_row = None

                output.write(
                    render_to_string(template_name="common/taric/end_envelope.xml")
                )
                logger.info("Import complete")

    def render_transaction(
        self, workbasket: WorkBasket, models: List[TrackedModel]
    ) -> str:
        return render_to_string(
            template_name="workbaskets/taric/transaction.xml",
            context={
                "tracked_models": map(self.serializer.to_representation, models),
                "transaction_id": self.transaction_counter(),
                "counter_generator": counter_generator,
                "message_counter": self.message_counter,
            },
        )
