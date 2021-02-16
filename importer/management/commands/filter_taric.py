import logging
import xml.etree.ElementTree as ET
import xml.etree.ElementTree as etree
from collections import defaultdict
from datetime import date
from datetime import timedelta
from enum import Enum
from io import StringIO
from typing import Any
from typing import Dict
from typing import Iterator
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union
from xml.etree.ElementTree import Element
from xml.etree.ElementTree import ElementTree

import xlrd
from django.core.management import BaseCommand
from typing_extensions import Literal
from xlrd.sheet import Cell

from commodities.models import GoodsNomenclature
from common.renderers import counter_generator
from importer.management.commands.patterns import BREXIT
from importer.management.commands.patterns import Counter
from importer.management.commands.patterns import MeasureEndingPattern
from importer.management.commands.patterns import OldMeasureRow
from importer.management.commands.patterns import parse_date
from importer.management.commands.utils import EnvelopeSerializer
from importer.management.commands.utils import col
from importer.namespaces import nsmap
from importer.parsers import ElementParser
from importer.taric import EnvelopeParser
from measures.models import FootnoteAssociationMeasure
from measures.models import Measure
from measures.models import MeasureComponent
from measures.models import MeasureCondition
from measures.models import MeasureConditionComponent
from measures.models import MeasureExcludedGeographicalArea
from regulations.models import Amendment
from regulations.models import Regulation

logger = logging.getLogger(__name__)


XML_CHUNK_SIZE = 4096 * 1024


class xml_dict(dict):
    """A `dict` object that also retains the source XML data."""

    def set_xml(self, xml: Element) -> None:
        self.xml = xml


class TriggerType(Enum):
    REGULATION = "Regulation"
    NOMENCLATURE = "Nomenclature"


class TriggeredMeasureEnd:
    def __init__(self, row: List[Cell]) -> None:
        self.old_measure = OldMeasureRow(row)
        self.triggering_regulation_role = str(int(row[col("AD")].value))
        self.triggering_regulation_id = str(row[col("AE")].value)
        self.end_date = parse_date(row[col("AF")].value)
        self.transaction = str(row[col("AG")].value)
        self.trigger_type = TriggerType(str(row[col("AH")].value))

    @property
    def trigger_key(self) -> Any:
        if self.trigger_type == TriggerType.REGULATION:
            return (self.triggering_regulation_role, self.triggering_regulation_id)
        elif self.trigger_type == TriggerType.NOMENCLATURE:
            return self.old_measure.goods_nomenclature_sid


class TriggeredMeasureTerminator:
    def __init__(
        self,
        filename: str,
        record_sequence: Counter,
        message_sequence: Counter,
        transaction_sequence: Counter,
    ) -> None:
        self.record_sequence = record_sequence
        self.message_sequence = message_sequence
        self.transaction_sequence = transaction_sequence
        self.triggers = self.load_triggers(filename)
        self.measure_ender = MeasureEndingPattern()

    def post_transaction(self, transaction: Dict[str, Any]) -> Iterator[Element]:
        for message in transaction["message"]:
            assert len(message["record"]) == 1
            record = message["record"][0]
            record_code = str(record["record_code"])
            subrecord_code = str(record["subrecord_code"])
            trigger_key = None

            if (
                record_code == Regulation.record_code
                and subrecord_code == Regulation.subrecord_code
            ):
                trigger_key = (
                    str(record["base_regulation"]["role_type"]),
                    str(record["base_regulation"]["regulation_id"]),
                )
            elif (
                record_code == Amendment.record_code
                and subrecord_code == Amendment.subrecord_code
            ):
                trigger_key = (
                    str(record["modification_regulation"]["role_type"]),
                    str(record["modification_regulation"]["regulation_id"]),
                )

            yield from self.run_triggers(trigger_key)

    def pre_transaction(self, transaction: Dict[str, Any]) -> Iterator[Element]:
        for message in transaction["message"]:
            assert len(message["record"]) == 1
            record = message["record"][0]
            record_code = str(record["record_code"])
            subrecord_code = str(record["subrecord_code"])
            trigger_key = None

            if (
                record_code == GoodsNomenclature.record_code
                and subrecord_code == GoodsNomenclature.subrecord_code
            ):
                trigger_key = int(record["goods_nomenclature"]["sid"])

            yield from self.run_triggers(trigger_key)

    def run_triggers(self, trigger_key: Any) -> Iterator[Element]:
        if trigger_key in self.triggers:
            triggered_ends = self.triggers[trigger_key]
            for triggered_end in triggered_ends:
                logger.info(
                    "Triggered end of %s",
                    triggered_end.old_measure.measure_sid,
                )
                models = list(
                    self.measure_ender.end_date_measure(
                        old_row=triggered_end.old_measure,
                        terminating_regulation=Regulation.objects.get(
                            regulation_id=triggered_end.triggering_regulation_id,
                            role_type=triggered_end.triggering_regulation_role,
                        ),
                        new_start_date=triggered_end.end_date + timedelta(days=1),
                    ),
                )
                output = StringIO()
                with EnvelopeSerializer(
                    output,
                    0,
                    self.transaction_sequence,
                    self.message_sequence,
                ) as env:
                    env.render_transaction(models)

                envelope = ET.fromstring(output.getvalue())
                txn = envelope.find(".//env:transaction", namespaces=nsmap)
                assert txn
                yield txn
            del self.triggers[trigger_key]

    def load_triggers(self, filename: str) -> Dict[Any, List[TriggeredMeasureEnd]]:
        triggers_book = xlrd.open_workbook(filename)
        sheet = triggers_book.sheet_by_index(0)
        rows = sheet.get_rows()
        next(rows)
        triggers = (TriggeredMeasureEnd(row) for row in rows)
        trigger_dict = defaultdict(lambda: [])
        for trigger in triggers:
            trigger_dict[trigger.trigger_key].append(trigger)
        return trigger_dict


class PassiveMeasureFilter:
    def __init__(
        self,
        record_sequence: Counter,
        message_sequence: Counter,
        transaction_sequence: Counter,
    ) -> None:
        self.record_sequence = record_sequence
        self.message_sequence = message_sequence
        self.transaction_sequence = transaction_sequence

        self.measure_kept_sids = set()
        self.measure_dropped_sids = set()
        self.measure_condition_kept_sids = set()
        self.measure_condition_dropped_sids = set()

    def handle_transaction(self, transaction: xml_dict) -> Iterator[Element]:
        any_keep = False
        new_id = None
        for message in transaction["message"]:
            assert len(message["record"]) == 1
            record = message["record"][0]
            keep = self.handle_record(record)
            any_keep = any_keep or keep
            if keep:
                if new_id is None:
                    new_id = self.transaction_sequence()
                seq = record.xml.find("oub:record.sequence.number", nsmap)
                seq.text = str(self.record_sequence())
                txn = record.xml.find("oub:transaction.id", nsmap)
                txn.text = str(new_id)
                message.xml.set("id", str(self.message_sequence()))
            else:
                transaction.xml.remove(message.xml)
        if any_keep:
            assert new_id is not None
            transaction.xml.set("id", str(new_id))
            yield transaction.xml

    terminating_regulations = [
        # UKGT has replaced all measures of third country type
        (
            (lambda m: m["measure_type__sid"] in ["103", "105"]),
            ("C2100001", "1"),
        ),
        # GSP replaces all measures for GSP geographies
        (
            (lambda m: m["geographical_area__area_id"] in ["2020", "2005", "2027"]),
            ("C2100002", "1"),
        ),
        # Suspensions SI replaced all measure of autonomous suspension type
        (
            (lambda m: m["measure_type__sid"] in ["112", "115"]),
            ("C2100003", "1"),
        ),
        # Disputes SI replaced all additional duties
        (
            (lambda m: m["measure_type__sid"] in ["695"]),
            ("C2100004", "1"),
        ),
    ]

    def find_terminating_regulation(self, measure: Dict) -> Optional[Tuple[str, str]]:
        for pred, reg in self.terminating_regulations:
            if pred(measure):
                return reg
        return None

    Tags = Union[
        Literal["oub:validity.end.date"],
        Literal["oub:justification.regulation.role"],
        Literal["oub:justification.regulation.id"],
    ]

    def update_measure(self, xml: Element, tag: Tags, value: str):
        """
        Set the tag in the measure XML to the new value.

        If the tag does not exist, create a new tag and add it before the
        "stopped.flag" element (so we assume we are adding end date or
        justification regulation)
        """
        element = xml.find(tag, nsmap)
        if element is None:
            stopped = xml.find("oub:stopped.flag", nsmap)
            assert stopped is not None
            index = list(xml).index(stopped)
            element = Element(tag)
            xml.insert(index, element)
        element.text = value

    def handle_record(self, record: xml_dict) -> bool:
        record_code = str(record["record_code"])
        subrecord_code = str(record["subrecord_code"])
        if record_code == Measure.record_code:
            # This is a measure-family record. If this is a measure record we
            # will have all of the appropriate information to work out if we
            # want to keep it or not.
            if subrecord_code == Measure.subrecord_code:
                measure = record["measure"]
                start_date = date.fromisoformat(measure["valid_between"]["lower"])
                end_date = (
                    date.fromisoformat(measure["valid_between"]["upper"])
                    if "upper" in measure["valid_between"]
                    else None
                )
                sid = measure["sid"]
                start_before_brexit = start_date < BREXIT
                ends_after_brexit = end_date is None or end_date >= BREXIT
                terminating_regulation = self.find_terminating_regulation(
                    record["measure"],
                )

                if terminating_regulation:
                    # We have already terminated measures of this type.
                    # If we have end-dated the measure, we need to preserve the
                    # end date. If we have deleted the measure, we output
                    # nothing.
                    if start_before_brexit and ends_after_brexit:
                        # End dated
                        self.measure_kept_sids.add(sid)
                        xml = measure.xml

                        if sid in [
                            "3785449",
                            "3785450",
                            "3785451",
                            "3785452",
                            "3785453",
                            "3785454",
                            "3785455",
                            "3785456",
                            "3785457",
                            "3785458",
                            "3785459",
                            "3785460",
                            "3785461",
                            "3785462",
                            "3785463",
                        ]:
                            end_date = "2020-08-26"
                        elif sid in [
                            "3784976",
                            "3784977",
                            "3784978",
                            "3784979",
                            "3784980",
                            "3784981",
                            "3784982",
                            "3784983",
                            "3784984",
                            "3784985",
                            "3784986",
                            "3784987",
                            "3784988",
                            "3784989",
                            "3784990",
                        ]:
                            end_date = "2020-08-25"
                        else:
                            end_date = (BREXIT - timedelta(days=1)).strftime("%Y-%m-%d")

                        self.update_measure(xml, "oub:validity.end.date", end_date)
                        self.update_measure(
                            xml,
                            "oub:justification.regulation.role",
                            str(terminating_regulation[1]),
                        )
                        self.update_measure(
                            xml,
                            "oub:justification.regulation.id",
                            terminating_regulation[0],
                        )
                        logger.info("End-dated measure %s", sid)
                        return True
                    if start_before_brexit and not ends_after_brexit:
                        # Just output it verbatim
                        self.measure_kept_sids.add(sid)
                        return True

                    # Deleted – output nothing
                    assert not start_before_brexit
                    self.measure_dropped_sids.add(sid)
                    logger.info("Dropped measure %s", sid)
                    return False

                # We haven't touched measurse of this type yet.
                self.measure_kept_sids.add(sid)
                return True

            if subrecord_code == MeasureCondition.subrecord_code:
                measure_sid = record["measure_condition"]["dependent_measure__sid"]
                condition_sid = record["measure_condition"]["sid"]
                if measure_sid in self.measure_kept_sids:
                    self.measure_condition_kept_sids.add(condition_sid)
                    return True
                if measure_sid in self.measure_dropped_sids:
                    self.measure_condition_dropped_sids.add(condition_sid)
                    return False

                logger.warning(
                    "Dependent condition for unknown measure %s",
                    measure_sid,
                )
                self.measure_condition_kept_sids.add(condition_sid)
                return True

            if subrecord_code == MeasureConditionComponent.subrecord_code:
                condition_sid = record["measure_condition_component"]["condition__sid"]
                if condition_sid in self.measure_condition_kept_sids:
                    return True
                if condition_sid in self.measure_condition_dropped_sids:
                    return False

                logger.warning(
                    "Dependent component for unknown measure condition %s",
                    condition_sid,
                )
                return True

            if subrecord_code in [
                MeasureComponent.subrecord_code,
                FootnoteAssociationMeasure.subrecord_code,
                MeasureExcludedGeographicalArea.subrecord_code,
            ]:
                # If it is a measure component or condition we will
                # first look up the measure SID to work out what to do.
                if subrecord_code == MeasureComponent.subrecord_code:
                    measure_sid = record["measure_component"]["component_measure__sid"]
                elif subrecord_code == FootnoteAssociationMeasure.subrecord_code:
                    measure_sid = record["footnote_association_measure"][
                        "footnoted_measure__sid"
                    ]
                elif subrecord_code == MeasureExcludedGeographicalArea.subrecord_code:
                    measure_sid = record["measure_excluded_geographical_area"][
                        "modified_measure__sid"
                    ]
                else:
                    measure_sid = None

                if measure_sid in self.measure_kept_sids:
                    return True
                if measure_sid in self.measure_dropped_sids:
                    return False
                logger.warning("Dependent item for unknown measure %s", measure_sid)
                return True
            raise Exception("Unhandled measure family element: %s", record)

        # This record is not of interest and we can pass it through.
        return True


class Command(BaseCommand):
    help = "Import data from a TARIC XML file into TaMaTo"

    def add_arguments(self, parser):
        parser.add_argument(
            "taric3_file",
            help="The TARIC3 file to be parsed.",
            nargs="+",
            type=str,
        )
        parser.add_argument(
            "--output",
            help="The XML file to output to.",
            type=str,
        )
        parser.add_argument(
            "--id",
            help="The ID for the output envelope file.",
            type=str,
        )
        parser.add_argument(
            "--transaction-id",
            help="The transaction ID to start from.",
            type=int,
        )
        parser.add_argument(
            "-d",
            help="List a measure SID as having been deleted.",
            nargs="+",
            default=[],
            type=int,
        )
        parser.add_argument(
            "--triggers",
            help="A spreadsheet of old measure rows that will get removed.",
            type=str,
        )

    def parse_envelope(self, taric3_file) -> EnvelopeParser:
        xmlparser = etree.iterparse(taric3_file, ["start", "end", "start-ns"])
        ElementParser.data_class = xml_dict
        ElementParser.end_hook = xml_dict.set_xml
        handler = EnvelopeParser(save=False)

        for event, elem in xmlparser:
            if event == "start":
                handler.start(elem)

            if event == "start_ns":
                nsmap.update([elem])

            if event == "end":
                handler.end(elem)

        return handler

    def handle(self, *args, **options):
        for prefix, uri in nsmap.items():
            ET.register_namespace(prefix, uri)

        sequencers = [
            counter_generator(start=1),
            counter_generator(start=1),
            counter_generator(start=options["transaction_id"]),
        ]

        measure_filter = PassiveMeasureFilter(*sequencers)
        terminator = TriggeredMeasureTerminator(options["triggers"], *sequencers)

        handlers = [
            terminator.pre_transaction,
            measure_filter.handle_transaction,
            terminator.post_transaction,
        ]

        for sid in options["d"]:
            measure_filter.measure_dropped_sids.add(sid)

        output_envelope = Element("env:envelope", attrib={"id": options["id"] or "0"})
        for filename in options["taric3_file"]:
            with open(filename) as taric3_file:
                logger.info("Starting file %s", filename)
                envelope = self.parse_envelope(taric3_file=taric3_file)
            for transaction in envelope.data["transaction"]:
                for handler in handlers:
                    for output in handler(transaction):
                        assert (
                            output.tag
                            == "{urn:publicid:-:DGTAXUD:GENERAL:ENVELOPE:1.0}transaction"
                        ), output.tag
                        output_envelope.append(output)

        with open(options["output"], mode="w", encoding="utf-8") as out:
            ElementTree(output_envelope).write(out, encoding="unicode")
