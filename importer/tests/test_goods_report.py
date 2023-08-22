from os import path
from tempfile import NamedTemporaryFile
from typing import List
from xml.etree import ElementTree as ET

import pytest

from common.validators import UpdateType
from importer.goods_report import TARIC3_NAMESPACES
from importer.goods_report import GoodsReporter
from importer.goods_report import GoodsReportLine

TEST_FILES_PATH = path.join(path.dirname(__file__), "test_files")


@pytest.fixture()
def record_info() -> List[dict]:
    """Returns record info for Goods Nomenclature related record types."""
    record_info = [
        {
            "record_name": "Goods nomenclature",
            "record_code": "400",
            "subrecord_code": "00",
            "is_valid": True,
        },
        {
            "record_name": "Indent",
            "record_code": "400",
            "subrecord_code": "05",
            "is_valid": True,
        },
        {
            "record_name": "Goods nomenclature description period",
            "record_code": "400",
            "subrecord_code": "10",
            "is_valid": True,
        },
        {
            "record_name": "Goods nomenclature description",
            "record_code": "400",
            "subrecord_code": "15",
            "is_valid": True,
        },
        {
            "record_name": "Goods nomenclature origin",
            "record_code": "400",
            "subrecord_code": "35",
            "is_valid": True,
        },
        {
            "record_name": "Goods nomenclature successor",
            "record_code": "400",
            "subrecord_code": "40",
            "is_valid": True,
        },
    ]
    return record_info


@pytest.fixture()
def empty_record_element() -> ET.Element:
    """Returns an empty record element that can be used to initialise a
    `GoodsReportLine` instance."""
    ns_oub = TARIC3_NAMESPACES["oub"]
    ns_env = TARIC3_NAMESPACES["env"]
    empty_record_element = ET.fromstring(
        f"""
            <oub:record xmlns:oub="{ns_oub}" xmlns:env="{ns_env}">
                <oub:update.type>{UpdateType.CREATE}</oub:update.type>
            </oub:record>
            """,
    )
    return empty_record_element


def test_goods_reporter_record_is_reportable(record_info):
    """Test that `GoodsReporter._is_reportable()` returns `True` if record is a
    match by record code and subrecord code for those records that are to be
    included in the generated report, `False` otherwise."""
    taric_file = NamedTemporaryFile(suffix=".xml")
    goods_reporter = GoodsReporter(goods_file=taric_file)
    ns_oub = TARIC3_NAMESPACES["oub"]
    ns_env = TARIC3_NAMESPACES["env"]
    for record in record_info:
        record_element = ET.fromstring(
            f"""
            <oub:record xmlns:oub="{ns_oub}" xmlns:env="{ns_env}">
                <oub:record.code>{record["record_code"]}</oub:record.code>
                <oub:subrecord.code>{record["subrecord_code"]}</oub:subrecord.code>
            </oub:record>
            """,
        )
        assert goods_reporter._is_reportable(record_element) == record["is_valid"]


@pytest.mark.parametrize(
    "update_type",
    [
        UpdateType.UPDATE,
        UpdateType.DELETE,
        UpdateType.CREATE,
    ],
)
def test_goods_report_line_get_update_type(update_type):
    """Test that `GoodsReportLine` returns the TARIC update type of a record
    instance."""
    ns_oub = TARIC3_NAMESPACES["oub"]
    ns_env = TARIC3_NAMESPACES["env"]
    record_element = ET.fromstring(
        f"""
        <oub:record xmlns:oub="{ns_oub}" xmlns:env="{ns_env}">
            <oub:update.type>{update_type}</oub:update.type>
        </oub:record>
        """,
    )
    report_line = GoodsReportLine(
        containing_transaction_id="1",
        containing_message_id="1",
        record_element=record_element,
    )
    assert report_line.update_type == update_type.name


def test_goods_report_line_get_record_name(record_info):
    """Test that `GoodsReportLine` returns the record name of the matching
    record code and subrecord code."""
    ns_oub = TARIC3_NAMESPACES["oub"]
    ns_env = TARIC3_NAMESPACES["env"]
    for record in record_info:
        record_element = ET.fromstring(
            f"""
            <oub:record xmlns:oub="{ns_oub}" xmlns:env="{ns_env}">
                <oub:record.code>{record["record_code"]}</oub:record.code>
                <oub:subrecord.code>{record["subrecord_code"]}</oub:subrecord.code>
                <oub:update.type>{UpdateType.CREATE}</oub:update.type>
            </oub:record>
            """,
        )
        report_line = GoodsReportLine(
            containing_transaction_id="1",
            containing_message_id="1",
            record_element=record_element,
        )
        assert report_line.record_name == record["record_name"]


def test_goods_report_line_get_goods_nomenclature_id():
    """Test that `GoodsReportLine` returns the item id of the associated goods
    nomenclature instance."""
    ns_oub = TARIC3_NAMESPACES["oub"]
    ns_env = TARIC3_NAMESPACES["env"]
    item_id = "1234567890"
    record_element = ET.fromstring(
        f"""
            <oub:record xmlns:oub="{ns_oub}" xmlns:env="{ns_env}">
                <oub:goods.nomenclature.item.id>{item_id}</oub:goods.nomenclature.item.id>
                <oub:update.type>{UpdateType.CREATE}</oub:update.type>
            </oub:record>
            """,
    )
    report_line = GoodsReportLine(
        containing_transaction_id="1",
        containing_message_id="1",
        record_element=record_element,
    )
    assert report_line.goods_nomenclature_item_id == item_id


def test_goods_report_line_get_suffix():
    """Test that `GoodsReportLine` returns the suffix code of the related goods
    nomenclature instance."""
    ns_oub = TARIC3_NAMESPACES["oub"]
    ns_env = TARIC3_NAMESPACES["env"]
    suffix = "80"
    record_element = ET.fromstring(
        f"""
            <oub:record xmlns:oub="{ns_oub}" xmlns:env="{ns_env}">
                <oub:productline.suffix>{suffix}</oub:productline.suffix>
                <oub:update.type>{UpdateType.CREATE}</oub:update.type>
            </oub:record>
            """,
    )
    report_line = GoodsReportLine(
        containing_transaction_id="1",
        containing_message_id="1",
        record_element=record_element,
    )
    assert report_line.suffix == suffix

    # Also ensure suffix is returned when tag contains commonly occurring
    # "producline" typo (missing 't') in EU-generated TARIC files
    record_element = ET.fromstring(
        f"""
            <oub:record xmlns:oub="{ns_oub}" xmlns:env="{ns_env}">
                <oub:producline.suffix>{suffix}</oub:producline.suffix>
                <oub:update.type>{UpdateType.CREATE}</oub:update.type>
            </oub:record>
            """,
    )
    report_line = GoodsReportLine(
        containing_transaction_id="1",
        containing_message_id="1",
        record_element=record_element,
    )
    assert report_line.suffix == suffix


def test_goods_report_line_get_validity_start_date():
    """Test that `GoodsReportLine` returns the validity start date of a record
    instance."""
    ns_oub = TARIC3_NAMESPACES["oub"]
    ns_env = TARIC3_NAMESPACES["env"]
    start_date = "2023-01-01"
    record_element = ET.fromstring(
        f"""
            <oub:record xmlns:oub="{ns_oub}" xmlns:env="{ns_env}">
                <oub:validity.start.date>{start_date}</oub:validity.start.date>
                <oub:update.type>{UpdateType.CREATE}</oub:update.type>
            </oub:record>
            """,
    )
    report_line = GoodsReportLine(
        containing_transaction_id="1",
        containing_message_id="1",
        record_element=record_element,
    )
    assert report_line.validity_start_date == start_date


def test_goods_report_line_get_validity_end_date():
    """Test that `GoodsReportLine` returns the validity end date of a record
    instance."""
    ns_oub = TARIC3_NAMESPACES["oub"]
    ns_env = TARIC3_NAMESPACES["env"]
    end_date = "2023-01-01"
    record_element = ET.fromstring(
        f"""
            <oub:record xmlns:oub="{ns_oub}" xmlns:env="{ns_env}">
                <oub:validity.end.date>{end_date}</oub:validity.end.date>
                <oub:update.type>{UpdateType.CREATE}</oub:update.type>
            </oub:record>
            """,
    )
    report_line = GoodsReportLine(
        containing_transaction_id="1",
        containing_message_id="1",
        record_element=record_element,
    )
    assert report_line.validity_end_date == end_date


def test_goods_report_line_get_absorbed_goods_nomenclature_comment():
    """Test that `GoodsReportLine` returns details of the absorbed goods
    nomenclature as displayed in comments column."""
    ns_oub = TARIC3_NAMESPACES["oub"]
    ns_env = TARIC3_NAMESPACES["env"]
    commodity = "1234567890"
    absorbed_commodity = "9876543210"
    record_element = ET.fromstring(
        f"""
            <oub:record xmlns:oub="{ns_oub}" xmlns:env="{ns_env}">
                <oub:goods.nomenclature.item.id>{commodity}</oub:goods.nomenclature.item.id>
                <oub:absorbed.goods.nomenclature.item.id>{absorbed_commodity}</oub:absorbed.goods.nomenclature.item.id>
                <oub:update.type>{UpdateType.CREATE}</oub:update.type>
            </oub:record>
            """,
    )
    report_line = GoodsReportLine(
        containing_transaction_id="1",
        containing_message_id="1",
        record_element=record_element,
    )
    assert (
        report_line.comments
        == f"{commodity} is being absorbed into {absorbed_commodity}"
    )


def test_goods_report_line_get_derived_goods_nomenclature_comment():
    """Test that `GoodsReportLine` returns details of the derived goods
    nomenclature as displayed in comments column."""
    ns_oub = TARIC3_NAMESPACES["oub"]
    ns_env = TARIC3_NAMESPACES["env"]
    commodity = "9876543210"
    derived_commodity = "1234567890"
    record_element = ET.fromstring(
        f"""
            <oub:record xmlns:oub="{ns_oub}" xmlns:env="{ns_env}">
                <oub:goods.nomenclature.item.id>{commodity}</oub:goods.nomenclature.item.id>
                <oub:derived.goods.nomenclature.item.id>{derived_commodity}</oub:derived.goods.nomenclature.item.id>
                <oub:update.type>{UpdateType.CREATE}</oub:update.type>
            </oub:record>
            """,
    )
    report_line = GoodsReportLine(
        containing_transaction_id="1",
        containing_message_id="1",
        record_element=record_element,
    )
    assert report_line.comments == f"{derived_commodity} as origin to {commodity}"


def test_goods_report_line_get_description_comment():
    """Test that `GoodsReportLine` returns details of the description as
    displayed in comments column."""
    ns_oub = TARIC3_NAMESPACES["oub"]
    ns_env = TARIC3_NAMESPACES["env"]
    description = "A new description"
    record_element = ET.fromstring(
        f"""
            <oub:record xmlns:oub="{ns_oub}" xmlns:env="{ns_env}">
                <oub:description>{description}</oub:description>
                <oub:update.type>{UpdateType.CREATE}</oub:update.type>
            </oub:record>
            """,
    )
    report_line = GoodsReportLine(
        containing_transaction_id="1",
        containing_message_id="1",
        record_element=record_element,
    )
    assert report_line.comments == f"New description: {description}"


def test_goods_report_line_get_indents_comment():
    """Test that `GoodsReportLine` returns details of the indent number as
    displayed in comments column."""
    ns_oub = TARIC3_NAMESPACES["oub"]
    ns_env = TARIC3_NAMESPACES["env"]
    indents = "04"
    record_element = ET.fromstring(
        f"""
            <oub:record xmlns:oub="{ns_oub}" xmlns:env="{ns_env}">
                <oub:number.indents>{indents}</oub:number.indents>
                <oub:update.type>{UpdateType.CREATE}</oub:update.type>
            </oub:record>
            """,
    )
    report_line = GoodsReportLine(
        containing_transaction_id="1",
        containing_message_id="1",
        record_element=record_element,
    )
    assert report_line.comments == f"Number of indents: {indents}"


def test_goods_report_line_containing_ids(empty_record_element):
    """Test that `GoodsReportLine` returns the containing transaction id and
    containing message id."""
    containing_transaction_id = "1"
    containing_message_id = "1"
    report_line = GoodsReportLine(
        containing_transaction_id=containing_transaction_id,
        containing_message_id=containing_message_id,
        record_element=empty_record_element,
    )
    assert report_line.containing_transaction_id == containing_transaction_id
    assert report_line.containing_message_id == containing_message_id


def test_goods_report_line_empty_record(empty_record_element):
    """Test that `GoodsReportLine` returns an empty string when a record
    instance is empty."""
    report_line = GoodsReportLine(
        containing_message_id="1",
        containing_transaction_id="1",
        record_element=empty_record_element,
    )
    assert report_line.record_name == ""
    assert report_line.goods_nomenclature_item_id == ""
    assert report_line.suffix == ""
    assert report_line.validity_start_date == ""
    assert report_line.validity_end_date == ""
    assert report_line.comments == ""


def test_goods_report_line_as_list(empty_record_element):
    """Test that `GoodsReportLine` returns a report line as a list of report
    columns."""
    report_line = GoodsReportLine(
        containing_transaction_id="1",
        containing_message_id="1",
        record_element=empty_record_element,
    )
    assert len(report_line.as_list()) == len(report_line.COLUMNS)


def test_goods_report_line_csv_columns():
    """Test that `GoodsReportLine` returns a csv representation of column
    names."""
    csv_column_names = (
        "update_type,whats_being_updated,goods_nomenclature_code,"
        "suffix,validity_start_date,validity_end_date,comments,"
        "containing_transaction_id,containing_message_id\r\n"
    )
    assert GoodsReportLine.csv_column_names() == csv_column_names


def test_goods_report_line_as_csv():
    """Test that `GoodsReportLine` returns a csv representation of a report
    line."""
    ns_oub = TARIC3_NAMESPACES["oub"]
    ns_env = TARIC3_NAMESPACES["env"]
    record_name = "Goods nomenclature"
    record_code = "400"
    subrecord_code = "00"
    update_type = UpdateType.CREATE
    item_id = "1234567890"
    suffix = "80"
    start_date = "2023-01-01"
    end_date = "2023-12-31"
    comments = ""
    transaction_id = "1"
    message_id = "1"
    record_element = ET.fromstring(
        f"""
        <oub:record xmlns:oub="{ns_oub}" xmlns:env="{ns_env}">
            <oub:record.code>{record_code}</oub:record.code>
            <oub:subrecord.code>{subrecord_code}</oub:subrecord.code>
            <oub:update.type>{update_type}</oub:update.type>
                <oub:goods.nomenclature>
                    <oub:goods.nomenclature.item.id>{item_id}</oub:goods.nomenclature.item.id>
                    <oub:producline.suffix>{suffix}</oub:producline.suffix>
                    <oub:validity.start.date>{start_date}</oub:validity.start.date>
                    <oub:validity.end.date>{end_date}</oub:validity.end.date>
                </oub:goods.nomenclature>
        </oub:record>
        """,
    )
    report_line = GoodsReportLine(
        containing_transaction_id=transaction_id,
        containing_message_id=message_id,
        record_element=record_element,
    )
    assert (
        report_line.as_csv()
        == f"{update_type.name},{record_name},{item_id},{suffix},{start_date},{end_date},{comments},{transaction_id},{message_id}\r\n"
    )


def test_goods_report_markdown():
    """Test that `GoodsReport` returns a Markdown table representation of a
    report."""
    with open(f"{TEST_FILES_PATH}/goods.xml", "rb") as taric_file:
        goods_reporter = GoodsReporter(taric_file)
        goods_report = goods_reporter.create_report()
    with open(f"{TEST_FILES_PATH}/goods_xml_report.md", "rt") as md_file:
        assert goods_report.markdown() == md_file.read()
