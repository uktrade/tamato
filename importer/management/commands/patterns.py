import logging
from datetime import datetime
from datetime import timedelta
from typing import Dict
from typing import Generic
from typing import Iterator
from typing import List
from typing import Optional
from typing import TypeVar

import pytz
import xlrd
from psycopg2._range import DateTimeTZRange
from xlrd.sheet import Cell

from additional_codes.models import AdditionalCode
from certificates.models import Certificate
from certificates.models import CertificateType
from commodities.models import GoodsNomenclature
from common.models import TrackedModel
from common.renderers import counter_generator
from common.validators import UpdateType
from footnotes.models import Footnote
from geo_areas.models import GeographicalArea
from importer.duty_sentence_parser import DutySentenceParser
from importer.management.commands.utils import blank, clean_item_id, convert_eur_to_gbp
from importer.management.commands.utils import Counter
from importer.management.commands.utils import maybe_max
from importer.management.commands.utils import maybe_min
from importer.management.commands.utils import NomenclatureTreeCollector
from importer.management.commands.utils import SeasonalRateParser
from measures.models import FootnoteAssociationMeasure, MonetaryUnit, MeasureComponent
from measures.models import Measure
from measures.models import MeasureAction
from measures.models import MeasureCondition
from measures.models import MeasureConditionCode
from measures.models import MeasureExcludedGeographicalArea
from measures.models import MeasureType
from quotas.models import QuotaOrderNumber
from regulations.models import Regulation
from workbaskets.models import WorkBasket

logger = logging.getLogger(__name__)

# The timezone of GB.
LONDON = pytz.timezone("Europe/London")

# The date of the end of the transition period,
# localized to the Europe/London timezone.
BREXIT = LONDON.localize(datetime(2021, 1, 1))


class OldMeasureRow:
    def __init__(self, old_row: List[Cell]) -> None:
        assert old_row is not None
        self.goods_nomenclature_sid = int(old_row[0].value)
        self.item_id = clean_item_id(old_row[1])
        self.inherited_measure = bool(old_row[6].value)
        assert not self.inherited_measure, "Old row should not be an inherited measure"
        self.measure_sid = int(old_row[7].value)
        self.measure_type = int(old_row[8].value)
        self.geo_sid = int(old_row[13].value)
        self.measure_start_date = self.parse_date(old_row[16].value)
        self.measure_end_date = blank(old_row[17].value, self.parse_date)
        self.regulation_role = int(old_row[18].value)
        self.regulation_id = str(old_row[19].value)
        self.order_number = blank(old_row[15].value, int)
        self.justification_regulation_role = blank(old_row[20].value, int)
        self.justification_regulation_id = blank(old_row[21].value, str)
        self.stopped = bool(old_row[24].value)
        self.additional_code = blank(old_row[22].value, str)
        self.additional_code_sid = blank(old_row[23].value, int)
        self.export_refund_sid = blank(old_row[25].value, int)
        self.reduction = blank(old_row[26].value, int)
        self.footnotes = self.parse_list(old_row[27].value)
        self.goods_nomenclature = GoodsNomenclature.objects.as_at(BREXIT).get(
            sid=self.goods_nomenclature_sid
        )

    def parse_date(self, value: str) -> datetime:
        return LONDON.localize(xlrd.xldate.xldate_as_datetime(value, datemode=0))

    def parse_list(self, value: str) -> List[str]:
        return list(filter(lambda s: s != "", map(str.strip, value.split(","))))


class MeasureCreatingPattern:
    """A pattern used for creating measures. This pattern will create a new
    measure along with any associated models such as components and conditions."""

    def __init__(
        self,
        generating_regulation: Regulation,
        workbasket: WorkBasket,
        duty_sentence_parser: DutySentenceParser,
        base_date: datetime = BREXIT,
        timezone=LONDON,
        exclusion_areas: Dict[str, GeographicalArea] = {},
        measure_sid_counter: Counter = counter_generator(),
        measure_condition_sid_counter: Counter = counter_generator(),
    ) -> None:
        self.seasonal_rate_parser = SeasonalRateParser(
            base_date=base_date, timezone=timezone
        )
        self.exclusion_areas = exclusion_areas
        self.generating_regulation = generating_regulation
        self.workbasket = workbasket
        self.duty_sentence_parser = duty_sentence_parser
        self.measure_sid_counter = measure_sid_counter
        self.measure_condition_sid_counter = measure_condition_sid_counter

    def get_default_measure_conditions(self, measure: Measure) \
            -> List[MeasureCondition]:
        presentation_of_certificate = MeasureConditionCode.objects.get(
            code="B",
        )
        certificate = Certificate.objects.get(
            sid="990",
            certificate_type=CertificateType.objects.get(sid="N"),
        )
        apply_mentioned_duty = MeasureAction.objects.get(
            code="27",
        )
        subheading_not_allowed = MeasureAction.objects.get(
            code="08",
        )
        return [
            MeasureCondition(
                sid=self.measure_condition_sid_counter(),
                dependent_measure=measure,
                component_sequence_number=1,
                condition_code=presentation_of_certificate,
                required_certificate=certificate,
                action=apply_mentioned_duty,
                update_type=UpdateType.CREATE,
                workbasket=self.workbasket,
            ),
            MeasureCondition(
                sid=self.measure_condition_sid_counter(),
                dependent_measure=measure,
                component_sequence_number=2,
                condition_code=presentation_of_certificate,
                action=subheading_not_allowed,
                update_type=UpdateType.CREATE,
                workbasket=self.workbasket,
            )
        ]

    def get_measure_components_from_duty_rate(self, measure: Measure, rate: str) \
            -> List[MeasureComponent]:
        try:
            components = []
            for component in self.duty_sentence_parser.parse(rate):
                component.component_measure = measure
                component.update_type = UpdateType.CREATE
                component.workbasket = self.workbasket
                components.append(component)
            return components
        except RuntimeError as ex:
            logger.error(f"Explosion parsing {rate}")
            raise ex

    def get_measure_excluded_geographical_areas(self, measure: Measure, geo_exclusion: Optional[str] = None) \
            -> MeasureExcludedGeographicalArea:
        exclusion = (
            self.exclusion_areas[geo_exclusion.strip()]
        )
        return MeasureExcludedGeographicalArea(
            modified_measure=measure,
            excluded_geographical_area=exclusion,
            update_type=UpdateType.CREATE,
            workbasket=self.workbasket,
        )

    def get_measure_footnotes(self, measure: Measure, footnotes: List[Footnote]) \
            -> List[FootnoteAssociationMeasure]:
        footnote_measures = []
        for footnote in footnotes:
            footnote_measures.append(
                FootnoteAssociationMeasure(
                    footnoted_measure=measure,
                    associated_footnote=footnote,
                    update_type=UpdateType.CREATE,
                    workbasket=self.workbasket,
                )
            )
        return footnote_measures

    def create(
        self,
        duty_sentence: str,
        geography: GeographicalArea,
        goods_nomenclature: GoodsNomenclature,
        new_measure_type: MeasureType,
        geo_exclusion: Optional[str] = None,
        order_number: Optional[QuotaOrderNumber] = None,
        authorised_use: bool = False,
        additional_code: AdditionalCode = None,
        validity_start: datetime = None,
        validity_end: datetime = None,
        footnotes: List[Footnote] = [],
    ) -> Iterator[TrackedModel]:
        assert goods_nomenclature.suffix == "80", "ME7 – must be declarable"

        for rate, start, end in self.seasonal_rate_parser.detect_seasonal_rates(
            duty_sentence
        ):
            actual_start = maybe_max(start, validity_start)
            actual_end = maybe_min(
                end, goods_nomenclature.valid_between.upper, validity_end
            )
            assert actual_start
            assert actual_end is None or actual_start <= actual_end

            new_measure = Measure(
                sid=self.measure_sid_counter(),
                measure_type=new_measure_type,
                geographical_area=geography,
                goods_nomenclature=goods_nomenclature,
                valid_between=DateTimeTZRange(actual_start, actual_end),
                generating_regulation=self.generating_regulation,
                terminating_regulation=(
                    self.generating_regulation if actual_end is not None else None
                ),
                order_number=order_number,
                additional_code=additional_code,
                update_type=UpdateType.CREATE,
                workbasket=self.workbasket,
            )
            yield new_measure

            if geo_exclusion:
                yield self.get_measure_exluded_geographical_areas(new_measure, geo_exclusion)

            for footnote in self.get_measure_footnotes(new_measure, footnotes):
                yield footnote

            if actual_end not in [validity_end, end]:
                logger.warning(
                    "Measure {} end date capped by {} end date: {:%Y-%m-%d}".format(
                        new_measure.sid, goods_nomenclature.item_id, actual_end
                    )
                )

            # If this is a measure under authorised use, we need to add
            # some measure conditions with the N990 certificate.
            if authorised_use:
                for condition in self.get_default_measure_conditions(new_measure):
                    yield condition

            for component in self.get_measure_components_from_duty_rate(new_measure, rate):
                yield component


class MeasureEndingPattern:
    """A pattern used for end-dating measures. This pattern will accept an old
    measure and will decide whether it needs to be end-dated (it starts before the
    specified date) or deleted (it starts after the specified date)."""

    def __init__(
        self,
        workbasket: WorkBasket,
        measure_types: Dict[int, MeasureType] = {},
        geo_areas: Dict[int, GeographicalArea] = {},
    ) -> None:
        self.workbasket = workbasket
        self.measure_types = measure_types
        self.geo_areas = geo_areas

    def end_date_measure(
        self,
        old_row: OldMeasureRow,
        terminating_regulation: Regulation,
        new_start_date: datetime = BREXIT,
    ) -> Iterator[TrackedModel]:
        if not old_row.inherited_measure:
            # Make sure we have loaded the types and areas we need
            if old_row.measure_type not in self.measure_types:
                self.measure_types[old_row.measure_type] = MeasureType.objects.get(
                    sid=old_row.measure_type
                )
            if old_row.geo_sid not in self.geo_areas:
                self.geo_areas[old_row.geo_sid] = GeographicalArea.objects.get(
                    sid=old_row.geo_sid
                )

            # If the old measure starts after Brexit, we instead
            # need to delete it and it will never come into force
            # If it ends before Brexit, we don't need to do anything!
            starts_after_brexit = old_row.measure_start_date >= new_start_date
            ends_before_brexit = (
                old_row.measure_end_date and old_row.measure_end_date < new_start_date
            )

            generating_regulation = Regulation.objects.get(
                role_type=old_row.regulation_role,
                regulation_id=old_row.regulation_id,
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
                justification_regulation = terminating_regulation
            else:
                # We are going to delete the measure but it has not been end-dated.
                assert old_row.measure_end_date is None
                justification_regulation = None

            if not ends_before_brexit:
                yield Measure(
                    sid=old_row.measure_sid,
                    measure_type=self.measure_types[old_row.measure_type],
                    geographical_area=self.geo_areas[old_row.geo_sid],
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
                            else new_start_date - timedelta(days=1)
                        ),
                    ),
                    generating_regulation=generating_regulation,
                    terminating_regulation=justification_regulation,
                    stopped=old_row.stopped,
                    reduction=old_row.reduction,
                    export_refund_nomenclature_sid=old_row.export_refund_sid,
                    update_type=(
                        UpdateType.DELETE if starts_after_brexit else UpdateType.UPDATE
                    ),
                    workbasket=self.workbasket,
                )
            else:
                logger.debug(
                    "Ignoring old measure %s as ends before Brexit", old_row.measure_sid
                )


OldRow = TypeVar("OldRow")
NewRow = TypeVar("NewRow")


class DualRowRunner(Generic[OldRow, NewRow]):
    def __init__(
        self,
        old_rows: NomenclatureTreeCollector[List[OldRow]],
        new_rows: NomenclatureTreeCollector[NewRow],
    ) -> None:
        self.old_rows = old_rows
        self.new_rows = new_rows

    def handle_rows(
        self, old_row: Optional[OldRow], new_row: Optional[NewRow]
    ) -> Iterator[None]:
        logger.debug(
            "Have old row for GN: %s. Have new row for GN: %s",
            old_row.goods_nomenclature.sid
            if old_row is not None and old_row.goods_nomenclature is not None
            else None,
            new_row.goods_nomenclature.sid
            if new_row is not None and new_row.goods_nomenclature is not None
            else None,
        )

        # Push the new row into the tree, but only if we found a CC for it
        # Initialize the old row tree with the same subtree if it is not yet set
        new_waiting = (
            new_row is not None
            and new_row.goods_nomenclature is not None
            and not self.new_rows.add(new_row.goods_nomenclature, new_row)
        )
        if self.old_rows.root is None:
            self.old_rows.root = self.new_rows.root

        # Push the old row into the tree, adding to any rows already for this CC
        # Initialize the new row tree with the same subtree if it is not yet set
        if old_row is not None and old_row.goods_nomenclature is not None:
            if old_row.goods_nomenclature in self.old_rows:
                roots = [
                    root
                    for root in self.old_rows.buffer()
                    if root[0] == old_row.goods_nomenclature
                ]
                assert len(roots) == 1
                logger.debug(
                    "Adding to old context (len %s) when adding cc %s [%s]",
                    len(roots[0][1]),
                    old_row.goods_nomenclature.item_id,
                    old_row.goods_nomenclature.sid,
                )
                rows = [*roots[0][1], old_row]
            else:
                logger.debug(
                    "Ignoring old context when adding cc %s [%s]",
                    old_row.goods_nomenclature.item_id,
                    old_row.goods_nomenclature.sid,
                )
                rows = [old_row]

            old_waiting = not self.old_rows.add(old_row.goods_nomenclature, rows)
        else:
            old_waiting = False

        if self.new_rows.root is None:
            self.new_rows.root = self.old_rows.root

        if old_waiting or new_waiting:
            # A row was rejected by the collector
            # The collector is full and we should process it
            logger.debug(
                f"Collector full with {len(self.old_rows.roots)} old (waiting {old_waiting})"
                f" and {len(self.new_rows.roots)} new (waiting {new_waiting})"
            )
            yield

            self.old_rows.reset()
            self.new_rows.reset()
            for transaction in self.handle_rows(
                old_row if old_waiting else None,
                new_row if new_waiting else None,
            ):
                yield transaction

        else:
            return iter([])
