import logging
import os
from dataclasses import dataclass
from typing import Generator
from typing import List
from typing import TextIO
from xml.etree import ElementTree as ET

from common.validators import UpdateType

logger = logging.getLogger(__name__)


TARIC3_NAMESPACES = {
    "env": "urn:publicid:-:DGTAXUD:GENERAL:ENVELOPE:1.0",
    "oub": "urn:publicid:-:DGTAXUD:TARIC:MESSAGE:1.0",
}
"""XML namespaces used in valid XML envelopes."""


# Goods Nomenclature XML tag names.
GOODS_NOMENCLATURE_TAG = "oub:goods.nomenclature"
GOODS_NOMENCLATURE_INDENT_TAG = "oub:goods.nomenclature.indent"
GOODS_NOMENCLATURE_DESCRIPTION_PERIOD_TAG = "oub:goods.nomenclature.description.period"
GOODS_NOMENCLATURE_DESCRIPTION_TAG = "oub:goods.nomenclature.description"
GOODS_NOMENCLATURE_ORIGIN_TAG = "oub:goods.nomenclature.origin"
GOODS_NOMENCLATURE_SUCCESSOR_TAG = "oub:goods.nomenclature.successor"


@dataclass
class RecordInfo:
    """Informational class for Goods Nomenclature related record types."""

    xml_tag: str
    name: str
    record_code: str
    subrecord_code: str


RECORD_TAG_TO_RECORD_INFO_MAP = {
    GOODS_NOMENCLATURE_TAG: RecordInfo(
        GOODS_NOMENCLATURE_TAG,
        "Goods nomenclature",
        "400",
        "00",
    ),
    GOODS_NOMENCLATURE_INDENT_TAG: RecordInfo(
        GOODS_NOMENCLATURE_INDENT_TAG,
        "Indent",
        "400",
        "05",
    ),
    GOODS_NOMENCLATURE_DESCRIPTION_PERIOD_TAG: RecordInfo(
        GOODS_NOMENCLATURE_DESCRIPTION_PERIOD_TAG,
        "Goods nomenclature description period",
        "400",
        "10",
    ),
    GOODS_NOMENCLATURE_DESCRIPTION_TAG: RecordInfo(
        GOODS_NOMENCLATURE_DESCRIPTION_TAG,
        "Goods nomenclature description",
        "400",
        "15",
    ),
    GOODS_NOMENCLATURE_ORIGIN_TAG: RecordInfo(
        GOODS_NOMENCLATURE_ORIGIN_TAG,
        "Goods nomenclature origin",
        "400",
        "35",
    ),
    GOODS_NOMENCLATURE_SUCCESSOR_TAG: RecordInfo(
        GOODS_NOMENCLATURE_SUCCESSOR_TAG,
        "Goods nomenclature successor",
        "400",
        "40",
    ),
}
"""Dictionary mapping of Goods record tags to RecordInfo instances, each
representing a TARIC3 record that can appear in a goods report."""


RECORD_CODE_TO_RECORD_INFO_MAP = {
    f"{r.record_code}{r.subrecord_code}": r
    for r in RECORD_TAG_TO_RECORD_INFO_MAP.values()
}
"""Dictionary mapping of record code + subrecord code to RecordInfo
instances."""


class GoodsReportLine:
    """Report lines for specific types of record."""

    COLUMN_NAMES = (
        "update_type",
        "whats_being_updated",
        "goods_nomenclature_code",
        # TODO:
        # "suffix",
        # "validity_start_date",
        # "validity_end_date",
        # "comments",
        # "original_message_id",
        # "original_transaction_id",
    )
    """Column names used within generated reports."""

    def __init__(self, record_element: ET.Element) -> None:
        self.record_element = record_element

        # Report columns.
        self.update_type = self._get_update_type()
        self.record_name = self._get_record_name()
        self.goods_nomenclature_item_id = self._get_goods_nomenclature_item_id()

    @classmethod
    def stringified_column_names(cls, separator: str = ", "):
        """Return a concatenated, string representaiton of report column names
        separated by `separator."""
        return f"{separator}".join(cls.COLUMN_NAMES)

    def as_list(self) -> List[str]:
        """Return a report line as a list of report columns."""
        return [
            self.update_type,
            self.record_name,
            self.goods_nomenclature_item_id,
        ]

    def as_str(self, separator: str = ", ") -> str:
        """Return a report line as a string concatenation of report columns,
        each separated by `separator`."""
        return f"{separator}".join(self.as_list())

    def _get_update_type(self) -> str:
        """Get the TARIC update type - one of UPDATE, DELETE and CREATE."""
        update_type_id = self.record_element.findtext(
            "oub:update.type",
            namespaces=TARIC3_NAMESPACES,
        )
        try:
            return UpdateType(int(update_type_id)).name
        except:
            logger.info(
                f"Malformed update type information encountered, " f"{update_type_id}",
            )
            return "Unknown"

    def _get_record_name(self) -> str:
        """Get the human-readable name of record being updated."""
        record_code_match = self.record_element.findtext(
            "./oub:record.code",
            default="",
            namespaces=TARIC3_NAMESPACES,
        ).strip()
        subrecord_code_match = self.record_element.findtext(
            "./oub:subrecord.code",
            default="",
            namespaces=TARIC3_NAMESPACES,
        ).strip()
        return RECORD_CODE_TO_RECORD_INFO_MAP.get(
            f"{record_code_match}{subrecord_code_match}",
        ).name

    def _get_goods_nomenclature_item_id(self) -> str:
        """Get the item id of the associated goods nomenclature instance."""
        return self.record_element.findtext(
            ".//oub:goods.nomenclature.item.id",
            default="",
            namespaces=TARIC3_NAMESPACES,
        ).strip()

    def __str__(self) -> str:
        return self.as_str()


class GoodsReport:
    """
    Represents a report providing information about goods-related entities.

    A report can be externalised to a variety of formats via this class's
    methods.
    """

    report_lines: List[GoodsReportLine] = []
    """List of ReportLines representing reported records in the order that they
    appear within the TARIC3 XML file."""

    def save_xlsx(self, filepath: str) -> None:
        """Save report to an Excel file in xlsx file format."""
        # TODO: is filepath better replaced with a writable file object?
        # TODO: generate and save to Excel file format.
        print("TODO: implement Excel file creation.")

    def markdown(self) -> str:
        """Return report in markdown format."""
        # TODO: generate and return markdown text content.

    def save_markdown(self, filepath: str) -> None:
        """Save report in markdown format to a file located at filepath."""
        # TODO: is filepath better replaced with a writable file object?
        self.markdown()
        # TODO: save to file.
        print("TODO: implement markdown file creation.")

    def plaintext(
        self,
        separator: str = ", ",
        include_column_names: bool = False,
    ) -> str:
        """Return a plain-text representation of the report."""
        str_repr = ""
        if include_column_names:
            str_repr += GoodsReportLine.stringified_column_names() + "\n"
        for line in self.report_lines:
            str_repr += f"{line.as_str(separator)}\n"
        return str_repr


class GoodsReporter:
    """Parses and builds a goods report for a TARIC3 XML file."""

    def __init__(self, goods_file: TextIO) -> None:
        self.goods_file = goods_file

    def create_report(self) -> GoodsReport:
        """Create an instance of GoodsReport by parsing a TARIC3 XML file,
        extracting information relevant to a goods report."""

        base_filename = os.path.basename(self.goods_file.name)

        logger.debug(f"Begin generating report object for {base_filename}.")

        goods_report = GoodsReport()
        record_count = 0

        for record_element in self._iter_records():
            record_count += 1
            if self._is_reportable(record_element):
                report_line = GoodsReportLine(record_element)
                goods_report.report_lines.append(report_line)

        logger.debug(
            f"Found {len(goods_report.report_lines)} goods-related "
            f"records from a total of {record_count} records.",
        )
        logger.debug(f"Finished generating report object for {base_filename}.")

        return goods_report

    def _is_reportable(self, record_element: ET.Element) -> bool:
        """Returns True if record is a match by record code and subrecord code
        for those records that are to be included in the generated report, False
        otherwise."""

        record_code_match = record_element.findtext(
            "./oub:record.code",
            default="",
            namespaces=TARIC3_NAMESPACES,
        ).strip()
        subrecord_code_match = record_element.findtext(
            "./oub:subrecord.code",
            default="",
            namespaces=TARIC3_NAMESPACES,
        ).strip()
        return (
            f"{record_code_match}{subrecord_code_match}"
            in RECORD_CODE_TO_RECORD_INFO_MAP.keys()
        )

    def _iter_records(self) -> Generator[ET.Element, None, None]:
        """Generator returning an iterator over the records of the goods
        file."""
        tree = ET.parse(self.goods_file)
        root = tree.getroot()

        for transaction in root.iterfind(
            "./env:transaction",
            namespaces=TARIC3_NAMESPACES,
        ):
            for record in transaction.iterfind(
                "./env:app.message/oub:transmission/oub:record",
                namespaces=TARIC3_NAMESPACES,
            ):
                yield record
