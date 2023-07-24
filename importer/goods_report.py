import csv
import logging
import os
from dataclasses import dataclass
from io import BytesIO
from io import StringIO
from typing import Generator
from typing import List
from typing import TextIO
from typing import Tuple
from xml.etree import ElementTree as ET

from openpyxl import Workbook
from openpyxl.styles import Font

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

    COLUMNS = {
        "update_type": "Update type",
        "whats_being_updated": "What's being updated",
        "goods_nomenclature_code": "Goods nomenclature code",
        "suffix": "Suffix",
        "validity_start_date": "Validity start date",
        "validity_end_date": "Validity end date",
        # TODO:
        # "comments",
        "containing_transaction_id": "Containing transaction ID",
        "containing_message_id": "Containing message ID",
    }
    """Column name and description dict."""
    COLUMN_NAMES = list(COLUMNS.keys())
    """Column names used within generated reports."""
    COLUMN_DESCRIPTIONS = list(COLUMNS.values())
    """Column descriptions (humanised) used within generated reports."""

    def __init__(
        self,
        containing_transaction_id: str,
        containing_message_id: str,
        record_element: ET.Element,
    ) -> None:
        self.record_element = record_element

        # Report columns.
        self.update_type = self._get_update_type()
        self.record_name = self._get_record_name()
        self.goods_nomenclature_item_id = self._get_goods_nomenclature_item_id()
        self.suffix = self._get_suffix()
        self.validity_start_date = self._get_validity_start_date()
        self.validity_end_date = self._get_validity_end_date()
        self.containing_transaction_id = containing_transaction_id
        self.containing_message_id = containing_message_id

    @classmethod
    def csv_column_names(cls, delimiter: str = ",") -> str:
        """Return a csv (concatenated, string) representation of report column
        names delimited by `delimiter`."""
        return cls._csv_line(cls.COLUMN_NAMES)

    @classmethod
    def markdown_header(cls, align: str = "left") -> str:
        """
        Return a Markdown table header of report column names, with row text
        aligned according to `align`.

        Each column is delimited by a pipe (|), and delimiter row matches column
        width to improve readability of raw string output.
        """
        if align == "center":
            alignment = ":", ":"
        elif align == "right":
            alignment = "", "-:"
        else:
            alignment = ":-", ""
        column_names = ""
        delimiter_row = ""
        for column in cls.COLUMN_NAMES:
            col_width = len(column)
            if column == "whats_being_updated":
                # Double column width to accomodate longest possible cell value
                column_names += "|" + column + (" " * col_width) + "  "
                delimiter_row += (
                    "|" + alignment[0] + ("-" * (col_width * 2)) + alignment[1]
                )
            else:
                # Column width is sufficient
                column_names += "|" + column + "  "
                delimiter_row += "|" + alignment[0] + ("-" * col_width) + alignment[1]
        column_names += "|\n"
        delimiter_row += "|\n"
        return column_names + delimiter_row

    def as_list(self) -> List[str]:
        """Return a report line as a list of report columns."""
        return [
            self.update_type,
            self.record_name,
            self.goods_nomenclature_item_id,
            self.suffix,
            self.validity_start_date,
            self.validity_end_date,
            self.containing_transaction_id,
            self.containing_message_id,
        ]

    def as_csv(self, delimiter: str = ",") -> str:
        """Return a report line as a string concatenation of report columns,
        each delimited by `delimiter`."""
        return self._csv_line(self.as_list(), delimiter)

    def as_markdown_row(self) -> str:
        """Return a report line as a Markdown table row."""
        return self._markdown_row(self.as_list())

    @classmethod
    def _csv_line(cls, line: List, delimiter=",") -> str:
        string_io = StringIO()
        writer = csv.writer(string_io, delimiter=delimiter)
        writer.writerow(line)
        return string_io.getvalue()

    @classmethod
    def _markdown_row(cls, line: List) -> str:
        """
        Each row and cell within is delimited by a pipe (|).

        And table cells are padded (" ") to match column width to improve
        readability of raw string output.
        """
        # Column name padding not calculable using len()
        column_padding = 2
        table_row = ""
        for i, cell in enumerate(line):
            if i == 1:
                # Double padding to match doubled column width of "whats_being_updated"
                padding = " " * (
                    (len(cls.COLUMN_NAMES[i]) * 2) - len(cell) + column_padding
                )
            else:
                padding = " " * (len(cls.COLUMN_NAMES[i]) - len(cell) + column_padding)
            table_row += "|" + cell + padding
        return table_row + "|\n"

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

    def _get_suffix(self) -> str:
        """Get the suffix code of the related goods nomenclature instance."""
        suffix = self.record_element.findtext(
            ".//oub:productline.suffix",
            default="",
            namespaces=TARIC3_NAMESPACES,
        ).strip()
        if suffix:
            return suffix
        # Second attempt to find productline.suffix as the commonly occurring
        # "producline" typo (missing 't') in EU-generated TARIC files.
        return self.record_element.findtext(
            ".//oub:producline.suffix",
            default="",
            namespaces=TARIC3_NAMESPACES,
        ).strip()

    def _get_validity_start_date(self) -> str:
        """Get the validity start date of the record instance."""
        return self.record_element.findtext(
            ".//oub:validity.start.date",
            default="",
            namespaces=TARIC3_NAMESPACES,
        ).strip()

    def _get_validity_end_date(self) -> str:
        """Get the validity end date of the record instance."""
        return self.record_element.findtext(
            ".//oub:validity.end.date",
            default="",
            namespaces=TARIC3_NAMESPACES,
        ).strip()

    def __str__(self) -> str:
        return self.as_csv()


class GoodsReport:
    """
    Represents a report providing information about goods-related entities.

    A report can be externalised to a variety of formats via this class's
    methods.
    """

    report_lines: List[GoodsReportLine]
    """List of ReportLines representing reported records in the order that they
    appear within the TARIC3 XML file."""

    def __init__(self) -> None:
        self.report_lines = []

    def csv(
        self,
        delimiter: str = ",",
        include_column_names: bool = True,
    ) -> str:
        """Return a csv string representation of the report."""
        str_repr = ""
        if include_column_names:
            str_repr += GoodsReportLine.csv_column_names()
        for line in self.report_lines:
            str_repr += f"{line.as_csv(delimiter)}"
        return str_repr

    def markdown_table(
        self,
        align: str = "left",
    ) -> str:
        """Return a Markdown table representation of the report, with row text
        aligned according to `align`."""
        markdown_table = ""
        markdown_table += GoodsReportLine.markdown_header(align=align)
        for line in self.report_lines:
            markdown_table += f"{line.as_markdown_row()}"
        return markdown_table

    def xlsx_file(
        self,
        xlsx_io: BytesIO,
        include_column_names: bool = True,
    ) -> None:
        """Write report contents to a BytesIO object, xlsx_io, in Excel (xlsx)
        file format."""

        workbook = Workbook()
        sheet = workbook.active

        if include_column_names:
            column_names = GoodsReportLine.COLUMN_NAMES
            sheet.append(column_names)
            for cell in sheet[1]:
                cell.font = Font(bold=True)

        for line in self.report_lines:
            sheet.append(line.as_list())

        workbook.save(xlsx_io.name)


class GoodsReporter:
    """Parses a TARIC3 XML file in order to then build a goods report (an
    instance of `GoodsReport`)."""

    def __init__(self, goods_file: TextIO) -> None:
        self.goods_file = goods_file

    def create_report(self) -> GoodsReport:
        """Create an instance of GoodsReport by parsing a TARIC3 XML file,
        extracting information relevant to a goods report."""

        base_filename = os.path.basename(self.goods_file.name)

        logger.debug(f"Begin generating report object for {base_filename}.")

        goods_report = GoodsReport()
        record_count = 0

        for transaction_id, message_id, record_element in self._iter_records():
            record_count += 1

            if self._is_reportable(record_element):
                report_line = GoodsReportLine(
                    transaction_id,
                    message_id,
                    record_element,
                )
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

    def _iter_records(self) -> Generator[Tuple[str, str, ET.Element], None, None]:
        """
        Generator yielding each record in the parsed goods file, along with the
        ID of its containing transaction and ID of its containing message, as a
        tuple.

        For instance, a tuple of ("123456", "1", <ET.Element>) would be yielded
        on the first iteration of the following XML content:

        .. code-block:: python

            <?xml version="1.0" encoding="UTF-8"?>
            <env:envelope xmlns="urn:..." xmlns:env="urn:publicid:-:DGTAXUD:GENERAL:ENVELOPE:1.0" id="23800">
                <env:transaction id="12345678">
                    <env:app.message id="1">
                        <oub:transmission xmlns:oub="urn:publicid:-:DGTAXUD:TARIC:MESSAGE:1.0" xmlns:env="urn:publicid:-:DGTAXUD:GENERAL:ENVELOPE:1.0">
                            <oub:record>
                                ...
                            </oub:record>
                        </oub:transmission>
                    </env:app.message>
                </env:transaction>
                ...
            </env:envelope>
        """
        tree = ET.parse(self.goods_file)
        root = tree.getroot()

        for transaction in root.iterfind(
            "./env:transaction",
            namespaces=TARIC3_NAMESPACES,
        ):
            transaction_id = transaction.attrib.get("id", "")

            for message in transaction.iterfind(
                "./env:app.message",
                namespaces=TARIC3_NAMESPACES,
            ):
                message_id = message.attrib.get("id", "")

                for record in message.iterfind(
                    "./oub:transmission/oub:record",
                    namespaces=TARIC3_NAMESPACES,
                ):
                    yield transaction_id, message_id, record
