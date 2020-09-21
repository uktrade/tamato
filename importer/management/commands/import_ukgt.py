import logging
import re
from datetime import datetime
from typing import Dict
from typing import Iterator
from typing import List
from typing import Optional

import django.db
import pytz
import xlrd
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.template.loader import render_to_string
from psycopg2._range import DateTimeTZRange
from xlrd.sheet import Cell

import settings
from commodities.models import GoodsNomenclature
from common.models import TrackedModel
from common.renderers import counter_generator
from common.serializers import TrackedModelSerializer
from common.validators import UpdateType
from geo_areas.models import GeographicalArea
from importer.duty_sentence_parser import DutySentenceParser
from measures.models import DutyExpression
from measures.models import Measure
from measures.models import Measurement
from measures.models import MeasureType
from measures.models import MonetaryUnit
from measures.serializers import MeasureComponentSerializer
from measures.serializers import MeasureSerializer
from regulations.models import Group
from regulations.models import Regulation
from workbaskets.models import Transaction
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

logger = logging.getLogger(__name__)

LONDON = pytz.timezone("Europe/London")
BREXIT = datetime(2021, 1, 1, 0, 0, 0, tzinfo=LONDON)

TRADE_REMEDY_RATE = re.compile(r"^\(([\d\.]+%)\)")
SEASONAL_RATE = re.compile(r"([\d\.]+%) \((\d\d [A-Z]{3}) - (\d\d [A-Z]{3})\)")


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
            "--output", help="The filename to output to.", type=str, default="out.xml"
        )

    def setup(self, workbasket: WorkBasket, options: Dict) -> Iterator[TrackedModel]:
        self.third_country_duty = MeasureType.objects.get(sid="103")
        self.non_pref_under_end_use = MeasureType.objects.get(sid="105")
        self.erga_omnes = GeographicalArea.objects.as_at(BREXIT).get(area_id="1011")
        self.brexit_to_infinity = DateTimeTZRange(BREXIT, None)
        self.mfn_regulation_group = Group.objects.get(group_id="DNC")

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
                validity_start = datetime.strptime(start, r"%d %b")
                validity_end = datetime.strptime(end, r"%d %b")
                if validity_start.month > validity_end.month:
                    # This straddles a year boundary so
                    # we need to make one measure for BREXIT to end
                    # and then another for start to BREXIT+1
                    yield (rate, BREXIT, validity_end.replace(year=2020))
                    yield (
                        rate,
                        validity_start.replace(year=2020),
                        BREXIT.replace(year=2021),
                    )
                else:
                    # Both months are in one year, hence make them 2020
                    yield (
                        rate,
                        validity_start.replace(year=2020),
                        validity_end.replace(year=2020),
                    )
        else:
            # Non-seasonal rate!
            yield (duty_exp, BREXIT, None)

    def compare_rows(
        self, new_row: Optional[List[Cell]], old_row: Optional[List[Cell]]
    ) -> int:
        if new_row is None:
            return -1
        if old_row is None:
            return 1

        level = "CN8"  # new_row[0].value
        comm_code = new_row[3].value  # new_row[1].value
        new_item_id = comm_code if level == "CN10" else comm_code + "00"
        old_item_id = old_row[1].value
        logger.debug("Comparing old %s and new %s", old_item_id, new_item_id)

        if old_item_id < new_item_id:
            return -1
        elif old_item_id > new_item_id:
            return 1
        else:
            return 0

    def handle_row(
        self,
        workbasket: WorkBasket,
        new_row: Optional[List[Cell]],
        old_row: Optional[List[Cell]],
    ) -> Iterator[TrackedModel]:
        if old_row is None:
            logger.warning(
                f"New measure {new_row[3].value} did not match old measure – assuming measure type 103"
            )

        goods_nomenclature = None
        new_measure_type = self.third_country_duty

        if old_row:
            old_goods_nomenclature_sid = old_row[0].value
            inherited_measure = old_row[8].value
            old_measure_sid = old_row[9].value
            old_measure_type = int(old_row[10].value)
            old_geo_sid = old_row[15].value
            old_measure_start_date = old_row[18].value
            old_measure_end_date = old_row[19].value
            old_regulation_role = old_row[20].value
            old_regulation_id = old_row[21].value

            if old_measure_type == 103:
                old_measure_type = self.third_country_duty
            elif old_measure_type == 105:
                old_measure_type = self.non_pref_under_end_use
            else:
                raise CommandError(old_measure_type)
            new_measure_type = old_measure_type

            goods_nomenclature = GoodsNomenclature.objects.get(
                sid=old_goods_nomenclature_sid
            )

            if not inherited_measure:
                assert old_geo_sid == self.erga_omnes.sid
                regulation, _ = Regulation.objects.get_or_create(
                    role_type=old_regulation_role,
                    regulation_id=old_regulation_id,
                    regulation_group=self.mfn_regulation_group,
                    valid_between=self.brexit_to_infinity,  # doesn't matter
                    approved=True,
                    update_type=UpdateType.CREATE,
                    workbasket=workbasket,
                )
                regulation.save()
                yield Measure(
                    sid=old_measure_sid,
                    measure_type=old_measure_type,
                    geographical_area=self.erga_omnes,
                    goods_nomenclature=goods_nomenclature,
                    valid_between=DateTimeTZRange(
                        datetime.strptime(old_measure_start_date, r"%Y-%m-%d")
                        if old_measure_start_date != ""
                        else None,
                        datetime.strptime(old_measure_end_date, r"%Y-%m-%d")
                        if old_measure_end_date != ""
                        else None,
                    ),
                    generating_regulation=regulation,
                    update_type=UpdateType.UPDATE,
                    workbasket=workbasket,
                )

        if new_row:
            if goods_nomenclature is None:
                level = "CN8"  # new_row[0].value
                comm_code = new_row[3].value  # new_row[1].value
                new_item_id = comm_code if level == "CN10" else comm_code + "00"
                goods_nomenclature = GoodsNomenclature.objects.as_at(BREXIT).get(
                    item_id=new_item_id,
                    suffix="80",
                )

            ukgt = self.clean_duty_sentence(new_row[13])  # [4])
            for rate, start, end in self.detect_seasonal_rates(ukgt):
                new_measure = Measure(
                    sid=123456,
                    measure_type=new_measure_type,
                    geographical_area=self.erga_omnes,
                    goods_nomenclature=goods_nomenclature,
                    valid_between=DateTimeTZRange(start, end),
                    generating_regulation=self.ukgt_si,
                    update_type=UpdateType.CREATE,
                    workbasket=workbasket,
                )
                yield new_measure

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
                        context={"envelope_id": "DIT200001"},
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

                while new_proceed or old_proceed:
                    handle_args = [None, None]  # for skipping
                    if old_row_number < options["old_skip_rows"]:
                        handle_args[1] = True
                    if new_row_number < options["new_skip_rows"]:
                        handle_args[0] = True

                    if handle_args == [None, None]:
                        try:
                            compare = self.compare_rows(new_row, old_row)
                            if compare < 0:
                                # Old row comes before new row
                                # Hence it is a row we are not replacing
                                handle_args = [None, old_row]
                            elif compare > 0:
                                # Old row comes after new row
                                # Hence new row is completely new
                                handle_args = [new_row, None]
                            else:  # compare == 0
                                # Rows compared equal
                                # Hence new row is replacing the old row
                                handle_args = [new_row, old_row]

                            tracked_models = []
                            for model in self.handle_row(workbasket, *handle_args):
                                # model.clean_fields()
                                # model.save()
                                logger.debug(model)
                                tracked_models.append(model)

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
        transaction, _ = Transaction.objects.get_or_create(workbasket=workbasket)
        transaction.save()

        return render_to_string(
            template_name="workbaskets/taric/transaction.xml",
            context={
                "tracked_models": map(self.serializer.to_representation, models),
                "transaction_id": transaction.id,
                "counter_generator": counter_generator,
                "message_counter": self.message_counter,
            },
        )
