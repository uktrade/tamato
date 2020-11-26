import logging
from collections import defaultdict
from datetime import timedelta
from enum import Enum
from functools import cached_property
from itertools import chain
from itertools import islice
from typing import Iterable
from typing import Iterator
from typing import List
from typing import Optional

import xlrd
from django.core.management import BaseCommand
from django.db import transaction
from psycopg2._range import DateTimeTZRange
from xlrd.sheet import Cell

from certificates.models import Certificate
from commodities.models import GoodsNomenclature
from common.models import TrackedModel
from common.util import validity_range_contains_range
from common.validators import UpdateType
from footnotes.models import Footnote
from geo_areas.models import GeographicalArea
from importer.management.commands.doc_importer import RowsImporter
from importer.management.commands.patterns import add_single_row
from importer.management.commands.patterns import BREXIT
from importer.management.commands.patterns import DualRowRunner
from importer.management.commands.patterns import LONDON
from importer.management.commands.patterns import MeasureCreatingPattern
from importer.management.commands.patterns import MeasureEndingPattern
from importer.management.commands.patterns import OldMeasureRow
from importer.management.commands.patterns import parse_date
from importer.management.commands.patterns import parse_list
from importer.management.commands.utils import blank
from importer.management.commands.utils import clean_duty_sentence
from importer.management.commands.utils import clean_item_id
from importer.management.commands.utils import col
from importer.management.commands.utils import EnvelopeSerializer
from importer.management.commands.utils import get_author
from importer.management.commands.utils import id_argument
from importer.management.commands.utils import MeasureContext
from importer.management.commands.utils import MeasureTreeCollector
from importer.management.commands.utils import output_argument
from importer.management.commands.utils import SeasonalRateParser
from importer.management.commands.utils import spreadsheet_argument, strint
from measures.models import Measurement
from measures.models import MeasureType
from quotas.models import QuotaAssociation
from quotas.models import QuotaDefinition
from quotas.models import QuotaOrderNumber
from quotas.models import QuotaOrderNumberOrigin
from quotas.models import QuotaOrderNumberOriginExclusion
from quotas.models import QuotaSuspension
from quotas.validators import AdministrationMechanism
from quotas.validators import QuotaCategory
from quotas.validators import SubQuotaType
from regulations.models import Group
from regulations.models import Regulation
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus
from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)


class QuotaType(Enum):
    CALENDAR = "Calendar year"
    NON_CALENDAR = "Non-calendar year"
    SEASONAL = "Seasonal"


class QuotaSource(Enum):
    PREFERENTIAL = "Pref"
    ORIGIN = "Origin"
    WTO = "WTO"


class NewQuotaRow:
    def __init__(self, row: List[Cell], origin: GeographicalArea) -> None:
        self.origin = origin
        self.origin_ids = parse_list(str(row[col("B")].value))
        if origin.area_id not in self.origin_ids:
            return
        self.excluded_origins = parse_list(str(row[col("C")].value))
        self.order_number = str(row[col("A")].value).strip()
        self.period_start = parse_date(row[col("D")])
        self.period_end = parse_date(row[col("E")])
        self.type = QuotaType(row[col("F")].value)
        self.volume = self.parse_volume(row[col("G")])
        self.interim_volume = blank(row[col("H")], self.parse_volume)
        self.unit = row[col("I")].value  # TODO convert to measurement
        self.qualifier = blank(row[col("J")].value, str)  # TODO convert to measurement
        self.parent_order_number = blank(row[col("L")].value, str)
        self.coefficient = blank(row[col("M")].value, str)
        self.source = QuotaSource(str(row[col("N")].value))
        self.suspension_start = blank(row[col("O")], parse_date)
        self.suspension_end = blank(row[col("P")], parse_date)
        self.certificate_str = blank(row[col("R")].value, str)
        self.end_use = bool(row[col("Q")].value)
        self.mechanism = (
            AdministrationMechanism.LICENSED
            if self.order_number.startswith("054")
            else AdministrationMechanism.FCFS
        )

    def parse_volume(self, cell: Cell) -> int:
        if cell.ctype == xlrd.XL_CELL_NUMBER:
            return int(cell.value)
        else:
            return int(cell.value.replace(",", ""))

    @cached_property
    def measurement(self) -> Measurement:
        kwargs = {"measurement_unit__code": self.unit}
        if self.qualifier is None:
            kwargs["measurement_unit_qualifier"] = None
        else:
            kwargs["measurement_unit_qualifier__code"] = self.qualifier

        return Measurement.objects.as_at(BREXIT).get(**kwargs)

    @cached_property
    def certificate(self) -> Optional[Certificate]:
        if self.certificate_str:
            logger.debug("Looking up certificate %s", self.certificate_str)
            return Certificate.objects.get(
                sid=self.certificate_str[1:],
                certificate_type__sid=self.certificate_str[0],
            )
        else:
            return None


class FTAQuotaImporter(RowsImporter):
    def setup(self) -> Iterator[TrackedModel]:
        self.brexit_to_infinity = DateTimeTZRange(BREXIT, None)
        self.quotas = {}
        return iter([])

    def compare_rows(self, new_row: Optional[NewQuotaRow], old_row: None) -> int:
        assert old_row is None
        return 1 if new_row else -1

    def handle_row(
        self, row: Optional[NewQuotaRow], old_row: None
    ) -> Iterator[Iterable[TrackedModel]]:
        self.quotas[row.order_number] = row

        # 1. Create a quota order number
        quota = QuotaOrderNumber(
            sid=self.counters["quota_order_number_id"](),
            order_number=row.order_number,
            mechanism=row.mechanism,
            category=QuotaCategory.PREFERENTIAL,
            valid_between=self.brexit_to_infinity,
            workbasket=self.workbasket,
            update_type=UpdateType.CREATE,
        )
        quota.save()

        # 2. Create origins and any exclusions
        quota_origin = QuotaOrderNumberOrigin(
            sid=self.counters["quota_order_number_origin_id"](),
            order_number=quota,
            geographical_area=row.origin,
            valid_between=self.brexit_to_infinity,
            workbasket=self.workbasket,
            update_type=UpdateType.CREATE,
        )
        quota_origin.save()
        to_output = [
            quota,
            quota_origin,
        ]

        for excluded_id in row.excluded_origins:
            excluded_area = GeographicalArea.objects.as_at(BREXIT).get(
                area_id=excluded_id
            )
            exclusion = QuotaOrderNumberOriginExclusion(
                origin=quota_origin,
                excluded_geographical_area=excluded_area,
                workbasket=self.workbasket,
                update_type=UpdateType.CREATE,
            )
            exclusion.save()
            to_output.append(exclusion)

        if quota.mechanism != AdministrationMechanism.LICENSED:
            yield to_output

        # If this is a seasonal quota that would normally have already started,
        # start it on 1 Jan and use the interim volume to set up the quota
        start_date = row.period_start
        end_date = row.period_end
        volume = row.volume
        if (
            row.type in [QuotaType.SEASONAL, QuotaType.NON_CALENDAR]
            and start_date.year < BREXIT.year
        ):
            # Dates in the sheet are not reliable – only days/months are correct
            # So assume that all the dates are for year 2021
            # If the end date comes before, it must be for 2022
            start_date = start_date.replace(year=BREXIT.year)
            end_date = end_date.replace(year=BREXIT.year)
            if end_date < start_date:
                end_date = end_date.replace(year=BREXIT.year + 1)
            assert end_date >= start_date

        # 3. Create a defn for 2021 from normal volume and start date to end date
        normal_qd = QuotaDefinition(
            sid=self.counters["quota_definition_id"](),
            order_number=quota,
            volume=volume,
            initial_volume=volume,
            measurement_unit=row.measurement.measurement_unit,
            measurement_unit_qualifier=row.measurement.measurement_unit_qualifier,
            maximum_precision=3,
            valid_between=DateTimeTZRange(
                lower=start_date,
                upper=end_date,
            ),
            quota_critical_threshold=90,
            description="",
            workbasket=self.workbasket,
            update_type=UpdateType.CREATE,
        )
        normal_qd.save()
        if quota.mechanism != AdministrationMechanism.LICENSED:
            yield [normal_qd]

        # 4. Create a defn for 2021 from interim volume and Jan 01 to start date
        if row.type == QuotaType.NON_CALENDAR and start_date > BREXIT:
            interim_end = start_date - timedelta(days=1)
            assert interim_end >= BREXIT

            interim_qd = QuotaDefinition(
                sid=self.counters["quota_definition_id"](),
                order_number=quota,
                volume=row.interim_volume,
                initial_volume=row.interim_volume,
                measurement_unit=row.measurement.measurement_unit,
                measurement_unit_qualifier=row.measurement.measurement_unit_qualifier,
                maximum_precision=3,
                valid_between=DateTimeTZRange(
                    lower=BREXIT,
                    upper=interim_end,
                ),
                quota_critical_threshold=90,
                description="",
                workbasket=self.workbasket,
                update_type=UpdateType.CREATE,
            )
            interim_qd.save()
            if quota.mechanism != AdministrationMechanism.LICENSED:
                yield [interim_qd]

        if row.parent_order_number:
            assert row.type == QuotaType.CALENDAR, row
            main_quota = QuotaDefinition.objects.get(
                order_number__order_number=row.parent_order_number,
            )

            association = QuotaAssociation(
                main_quota=main_quota,
                sub_quota=normal_qd,
                sub_quota_relation_type=(
                    SubQuotaType.NORMAL
                    if row.coefficient in ["1.00", "1.0", "1"]
                    else SubQuotaType.EQUIVALENT
                ),
                coefficient=row.coefficient,
                workbasket=self.workbasket,
                update_type=UpdateType.CREATE,
            )
            association.save()
            if quota.mechanism != AdministrationMechanism.LICENSED:
                yield [association]

        if row.suspension_start and row.suspension_end:
            assert row.type != QuotaType.NON_CALENDAR, "Need to handle both QDs"
            start = row.suspension_start.replace(year=BREXIT.year)
            end = row.suspension_end.replace(year=BREXIT.year)
            if start < normal_qd.valid_between.lower:
                start += relativedelta(years=1)
                end += relativedelta(years=1)
            assert start >= normal_qd.valid_between.lower
            assert end <= normal_qd.valid_between.upper
            suspension = QuotaSuspension(
                sid=self.counters["quota_suspension_id"](),
                quota_definition=normal_qd,
                valid_between=DateTimeTZRange(start, end),
                workbasket=self.workbasket,
                update_type=UpdateType.CREATE,
            )
            suspension.save()
            if quota.mechanism != AdministrationMechanism.LICENSED:
                yield [suspension]


class TransitionCategory(Enum):
    COUNTRY_NOT_IN_SCOPE = "A1"
    PREF_ALREADY_ZERO = "A2"
    BOTH_AD_VALOREM_NON_ZERO = "B1"
    # CET is AV and preferential rate is non-AV. Preference remains unchanged.
    CET_AV_PREF_NON_AV = "B2"
    # CET is AV and preferential rate has AC. Preference becomes zero.
    CET_AV_PREF_HAS_AC = "B3"
    # CET and preference are specific. Preference remains unchanged.
    BOTH_SPECIFIC_DUTY = "C1"
    # CET and preference compound. Preference remains unchanged.
    BOTH_COMPOUND_DUTY = "C2"
    # CET compound and preference AV. Preference remains unchanged.
    CET_COMPOUND_PREF_AV = "C3"
    # CET seasonal. Preference remains unchanged.
    CET_SEASONAL = "D1"
    # CET is seasonal/minmax. Preference remains unchanged.
    CET_SEASONAL_MINMAX = "D2"
    # CET is specific with minmax. Preference remains unchanged.
    CET_SPECIFIC_DUTY_MINMAX = "D3"
    # CET is EPS. Preference is set to rate in highest price band, which is zero.
    CET_EPS_PREF_HIGHEST_ZERO = "E1"
    # CET is EPS. Preference is set to rate in highest price band, which is ad valorem.
    CET_EPS_PREF_HIGHEST_AV = "E2"
    # CET is EPS. Preference is set to rate in highest price band, which is non-ad valorem.
    CET_EPS_PREF_HIGHEST_NON_AV = "E3"
    # CET is EPS and preference is ad valorem. Preference remains unchanged.
    CET_EPS_PREF_AV = "E4"
    # CET is EPS and preference is non-ad valorem. Preference remains unchanged.
    CET_EPS_PREF_NON_AV = "E5"
    # set to zero (renegotiated)
    PREF_ZERO = "J1"
    # Meursing, preference becomes zero
    MEURSING_PREF_ZERO = "M1"
    # Meursing; set to AV element of preferential rate
    MEURSING_PREF_AV = "M2"
    # Meursing; preferential rate is specific; retain specific rate
    MEURSING_PREF_SD = "M3"
    # special case; CET is 5.5%, but UKGT is 4% for one line and free for another line.
    # Pref can remain 2% unless LDR applies.
    # With LDR we need to split the preference measure into two lines.
    SPLIT_SPECIAL_CASE = "S1"
    # special case for Chile; pref defined as one third of MFN at time of import,
    # requires reduction from 8% to 20/3 = 6.7% (rounded)
    CHILE_SPECIAL_CASE = "S2"
    # expired
    EXPIRED = "X"


class TransitionStaging(Enum):
    NONE = "."
    ANDEAN_COLOMBIA = "COL"
    ANDEAN_ECUADOR = "ECU"
    ANDEAN_PERU = "PER"
    CANADA = "CAN"
    SOUTH_AFRICA = "ZAF"
    CENTRAL_AMERICA = "Central America"
    UKRAINE = "UKR"


class MainMeasureRow:
    def __init__(self, row: List[Cell], origin: GeographicalArea) -> None:
        self.category = TransitionCategory(str(row[col("AF")].value).split(":")[0])
        self.origin_id = str(row[col("K")].value)
        self.origin = origin
        if (
            self.category == TransitionCategory.COUNTRY_NOT_IN_SCOPE
            or self.origin.area_id != self.origin_id
        ):
            return
        self.row_id = strint(row[col("A")])
        self.item_id = clean_item_id(row[col("B")])
        self.measure_type_id = strint(row[col("I")])
        self.origin_description = str(row[col("L")].value)
        self.excluded_origin_description = str(row[col("M")].value)
        original_order_number = blank(row[col("N")].value, str)
        self.order_number = (
            original_order_number.replace("09", "05", 1)
            if original_order_number
            else None
        )
        self.start_date = parse_date(row[col("O")])
        self.end_date = blank(row[col("P")].value, lambda _: parse_date(row[col("P")]))
        self.duty_exp = clean_duty_sentence(row[col("AM")])
        self.staging = TransitionStaging(str(row[col("AO")].value).split(" - ")[0])

    @cached_property
    def goods_nomenclature(self) -> GoodsNomenclature:
        return GoodsNomenclature.objects.as_at(BREXIT).get(
            item_id=self.item_id, suffix="80"
        )

    @cached_property
    def measure_context(self) -> MeasureContext:
        return MeasureContext(
            self.measure_type_id,
            self.origin.sid,
            None,
            None,
            self.order_number,
            None,
            self.start_date,
            self.end_date,
        )


class StagedMeasureRow:
    sheet = ""
    staging_2021_column = str(None)

    def __init__(self, row: List[Cell]) -> None:
        self.row_id = strint(row[col("A")])
        self.item_id = clean_item_id(row[col("B")])
        self.duty_exp = clean_duty_sentence(row[col(self.staging_2021_column)])


class SouthAfricaStagingRow(StagedMeasureRow):
    sheet = "STG - South Africa"
    staging_2021_column = "BB"


class EcuadorStagingRow(StagedMeasureRow):
    sheet = "STG - Andean-Ecuador"
    staging_2021_column = "BC"


class ColombiaStagingRow(StagedMeasureRow):
    sheet = "STG - Andean-Colombia"
    staging_2021_column = "AY"


class PeruStagingRow(StagedMeasureRow):
    sheet = "STG - Andean-Peru"
    staging_2021_column = "AY"


class UkraineStagingRow(StagedMeasureRow):
    sheet = "STG - Ukraine"
    staging_2021_column = "AY"


class CentralAmericaStagingRow(StagedMeasureRow):
    sheet = "STG - CentralAmerica"
    staging_2021_column = "AX"


class CanadaStagingRow(StagedMeasureRow):
    sheet = "STG - Canada"
    staging_2021_column = "AY"


STAGED_COUNTRIES = {
    "ZA": SouthAfricaStagingRow,
    "EC": EcuadorStagingRow,
    "CO": ColombiaStagingRow,
    "PE": PeruStagingRow,
    "UA": UkraineStagingRow,
    "2200": CentralAmericaStagingRow,
    "CA": CanadaStagingRow,
}


CUSTOMS_UNION_EQUIVALENT_TYPES = {
    "106": "142",
    "147": "143",
}


class FTAMeasuresImporter(RowsImporter):
    def __init__(self, *args, staged_rows={}, quotas={}, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.staged_rows = staged_rows
        self.quotas = quotas

    def setup(self) -> Iterator[TrackedModel]:
        self.measure_types = {
            "142": MeasureType.objects.get(sid="142"),
            "143": MeasureType.objects.get(sid="143"),
            "145": MeasureType.objects.get(sid="145"),
            "146": MeasureType.objects.get(sid="146"),
        }
        self.old_rows = MeasureTreeCollector[OldMeasureRow](BREXIT)
        self.new_rows = MeasureTreeCollector[MainMeasureRow](BREXIT)
        self.row_runner = DualRowRunner(
            self.old_rows,
            self.new_rows,
            add_old_row=add_single_row,
            add_new_row=add_single_row,
        )
        self.seasonal_rate_parser = SeasonalRateParser(
            base_date=BREXIT,
            timezone=LONDON,
        )

        self.brexit_to_infinity = DateTimeTZRange(BREXIT, None)

        self.preferential_si, created = Regulation.objects.get_or_create(
            regulation_id="C2100006",
            defaults={
                "regulation_group": Group.objects.get(group_id="PRF"),
                "published_at": BREXIT,
                "approved": False,
                "valid_between": self.brexit_to_infinity,
                "workbasket": self.workbasket,
                "update_type": UpdateType.CREATE,
            },
        )

        self.measure_ender = MeasureEndingPattern(
            workbasket=self.workbasket,
            measure_types=self.measure_types,
        )

        self.measure_creator = MeasureCreatingPattern(
            generating_regulation=self.preferential_si,
            workbasket=self.workbasket,
            duty_sentence_parser=self.duty_sentence_parser,
            measure_sid_counter=self.counters["measure_id"],
            measure_condition_sid_counter=self.counters["measure_condition_id"],
            exclusion_areas={
                "Haiti": GeographicalArea.objects.as_at(BREXIT).get(area_id="HT"),
                "Panama": GeographicalArea.objects.as_at(BREXIT).get(area_id="PA"),
            },
        )

        return iter([])

    def handle_row(
        self, new_row: Optional[MainMeasureRow], old_row: Optional[OldMeasureRow]
    ) -> Iterator[List[TrackedModel]]:
        for _ in self.row_runner.handle_rows(old_row, new_row):
            for transaction in self.flush():
                yield transaction

    def flush(self) -> Iterator[List[TrackedModel]]:
        item_ids = defaultdict(list)
        # Send the old row to be end dated or removed
        for cc, row in self.old_rows.buffer():
            item_ids[cc].append(row)
            logger.debug("End-dating measure: %s", row.measure_sid)
            yield list(self.measure_ender.end_date_measure(row, self.preferential_si))

        # Create measures either for the single measure type or a mix
        for cc, row in self.new_rows.buffer():
            if cc in item_ids:
                matched_old_rows = item_ids[cc]
            else:
                ancestor_cc = [
                    root[0]
                    for root in self.old_rows.roots
                    if self.old_rows.within_subtree(cc, root)
                ]
                assert (
                    len(ancestor_cc) <= 1
                ), f"Looking for: {cc.item_id}[{cc.sid}], found {len(ancestor_cc)}"
                if len(ancestor_cc) == 1:
                    matched_old_rows = item_ids[ancestor_cc[0]]
                else:
                    matched_old_rows = []
            for old_row in matched_old_rows:
                assert old_row.measure_sid in self.measure_ender.old_sids

            for transaction in self.make_new_measure(row, matched_old_rows, cc):
                yield transaction

    def make_new_measure(
        self,
        row: MainMeasureRow,
        old_rows: List[OldMeasureRow],
        goods_nomenclature: GoodsNomenclature,
    ) -> Iterator[List[TrackedModel]]:
        if row.start_date.year < BREXIT.year - 1 and row.end_date is not None:
            # We will ignore dates that are not in 2020
            # because any seasonal preferences should appear again
            logger.warning(
                "Ignoring row %s because seasonal dates from previous years", row.row_id
            )
            return

        # 1. If this is a staged row, take it's new duty expression
        # from the staging sheet, else from the main sheet
        if row.staging != TransitionStaging.NONE:
            staged_row = self.staged_rows[row.row_id]
            duty_exp = staged_row.duty_exp
        else:
            duty_exp = row.duty_exp
        duty_exp = duty_exp.replace("tonne", "1,000 kg")

        if row.order_number:
            quotas = QuotaOrderNumber.objects.filter(
                order_number=row.order_number
            ).all()
            if not any(quotas):
                # Drop the measure if we are not transitioning the quota
                logger.warning(
                    "Dropping row %s because there is no matching quota %s",
                    row.row_id,
                    row.order_number,
                )
                return
            else:
                quota = quotas[0]
        else:
            quota = None

        # 2. If the preference is marked "A2: Pref already zero",
        # set the duty rate to 0%
        if row.category == TransitionCategory.PREF_ALREADY_ZERO:
            assert duty_exp == "."
            assert row.staging == TransitionStaging.NONE
            duty_exp = "0.00%"

        # Turkey: Where the measure type is currently "Customs Union" use
        # instead of the normal type.
        if row.origin.area_id == "TR":
            measure_type_id = CUSTOMS_UNION_EQUIVALENT_TYPES[row.measure_type_id]
        else:
            measure_type_id = row.measure_type_id
        measure_type = self.measure_types[measure_type_id]

        # `old_rows` is all the rows with the same item id but not necessarily
        # the same measure context
        footnote_ids = set(
            chain(
                r.footnotes
                for r in old_rows
                if r.measure_context == row.measure_context
            )
        )
        footnotes = [
            Footnote.objects.as_at(BREXIT).get(
                footnote_id=f[3:], footnote_type__footnote_type_id=f[0:2]
            )
            for f in footnote_ids
        ]

        if row.order_number in self.quotas:
            origin_certificate = self.quotas[row.order_number].certificate
            assert row.order_number is not None
        else:
            origin_certificate = None

        # 3. Otherwise, take the start (col O) and end (col P) dates
        # and use the same month and day for 2021, and apply the new rate in column AM.
        # Check that any attached quota has the same or greater validity period.
        for start, end in self.seasonal_rate_parser.correct_dates(
            row.start_date, row.end_date
        ):
            if quota:
                date_range = DateTimeTZRange(start, end)
                assert validity_range_contains_range(quota.valid_between, date_range)
                if not QuotaDefinition.objects.filter(
                    order_number=quota, valid_between__contains=date_range
                ).exists():
                    defns = QuotaDefinition.objects.filter(order_number=quota).all()
                    periods = "; ".join(
                        f"{defn.sid}: {defn.valid_between}" for defn in defns
                    )
                    logger.warning(
                        "No matching definition for %s contains %s. Options are: %s",
                        quota.order_number,
                        date_range,
                        periods,
                    )

            yield list(
                self.measure_creator.create(
                    duty_sentence=duty_exp,
                    geography=row.origin,
                    goods_nomenclature=goods_nomenclature,
                    geo_exclusion=row.excluded_origin_description,
                    new_measure_type=measure_type,
                    authorised_use=(measure_type_id in {"146", "145"}),
                    order_number=quota,
                    validity_start=start,
                    validity_end=end,
                    footnotes=footnotes,
                    proof_of_origin=origin_certificate,
                )
            )


class Command(BaseCommand):
    help = "Import spreadsheets of quotas and measures for trade agreements."

    def add_arguments(self, p):
        spreadsheet_argument(p, "new")
        spreadsheet_argument(p, "old")
        spreadsheet_argument(p, "quota")
        p.add_argument(
            "geographical_area",
            help="The name of the geographical area to import data for on this run.",
            nargs="+",
            type=str,
        )
        id_argument(p, "measure", 200000000)
        id_argument(p, "measure-condition", 200000000)
        id_argument(p, "quota-order-number")
        id_argument(p, "quota-order-number-origin")
        id_argument(p, "quota-definition")
        id_argument(p, "quota-suspension")
        id_argument(p, "envelope")
        id_argument(p, "transaction", 140)
        output_argument(p)

    @transaction.atomic
    def handle(self, *args, **options):
        author = get_author()

        quota_workbook = xlrd.open_workbook(options["quota-spreadsheet"])
        quota_sheet = quota_workbook.sheet_by_name("ALL")
        new_workbook = xlrd.open_workbook(options["new-spreadsheet"])
        schedule_sheet = new_workbook.sheet_by_name("MAIN")
        old_workbook = xlrd.open_workbook(options["old-spreadsheet"])
        old_worksheet = old_workbook.sheet_by_name("Sheet")

        with open(options["output"], mode="w", encoding="UTF8") as output:
            with EnvelopeSerializer(
                output,
                options["counters"]["envelope_id"](),
                options["counters"]["transaction_id"],
                max_envelope_size_in_mb=39,
            ) as env:
                for country in options["geographical_area"]:
                    origin = GeographicalArea.objects.as_at(BREXIT).get(area_id=country)

                    workbasket, _ = WorkBasket.objects.get_or_create(
                        title=f"Preferential data for {country}",
                        author=author,
                        status=WorkflowStatus.PUBLISHED,
                    )

                    quota_rows = islice(
                        quota_sheet.get_rows(), options["quota_skip_rows"], None
                    )
                    country_quota_rows = (
                        row
                        for row in (NewQuotaRow(row, origin) for row in quota_rows)
                        if country in row.origin_ids
                        and row.source in [QuotaSource.ORIGIN, QuotaSource.PREFERENTIAL]
                    )

                    staging_dict = {}
                    if country in STAGED_COUNTRIES:
                        logger.info("Loading staging information for %s", country)
                        StagedRowClass = STAGED_COUNTRIES[country]
                        staging_worksheet = new_workbook.sheet_by_name(
                            StagedRowClass.sheet
                        )
                        sheet_rows = islice(
                            staging_worksheet.get_rows(), options["new_skip_rows"], None
                        )
                        staging_rows = (StagedRowClass(row) for row in sheet_rows)
                        staging_dict = {row.row_id: row for row in staging_rows}

                    quota_importer = FTAQuotaImporter(
                        workbasket,
                        env,
                        counters=options["counters"],
                    )
                    quota_importer.import_sheets(country_quota_rows, iter([None]))

                    new_rows = islice(
                        schedule_sheet.get_rows(), options["new_skip_rows"], None
                    )
                    country_new_rows = (
                        row
                        for row in (MainMeasureRow(row, origin) for row in new_rows)
                        if row.origin_id == country
                    )

                    old_rows = islice(
                        old_worksheet.get_rows(), options["old_skip_rows"], None
                    )
                    country_old_rows = (
                        row
                        for row in (OldMeasureRow(row) for row in old_rows)
                        if row.geo_sid == origin.sid
                    )

                    importer = FTAMeasuresImporter(
                        workbasket,
                        env,
                        counters=options["counters"],
                        staged_rows=staging_dict,
                        quotas=quota_importer.quotas,
                    )
                    importer.import_sheets(country_new_rows, country_old_rows)

        for name, counter in options["counters"].items():
            logger.info("Next %s: %s", name, counter())

        transaction.set_rollback(True)
