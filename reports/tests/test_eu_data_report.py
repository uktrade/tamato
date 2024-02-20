import pytest
from reports.models import EUDataModel
from reports.reports.eu_data import Report as EUDataReport


@pytest.fixture
def eu_data_report():
    return EUDataReport()


@pytest.fixture
def mock_data():
    return [
        EUDataModel(
            goods_code="123",
            add_code="456",
            order_no=None,
            start_date=None,
            end_date=None,
            red_ind=None,
            origin=None,
            measure_type=None,
            legal_base=None,
            duty=None,
            origin_code=None,
            meas_type_code=None,
            goods_nomenclature_exists=None,
            geographical_area_exists=None,
            measure_type_exists=None,
            measure_exists=None,
        ),
        EUDataModel(
            goods_code="789",
            add_code="012",
            order_no=None,
            start_date=None,
            end_date=None,
            red_ind=None,
            origin=None,
            measure_type=None,
            legal_base=None,
            duty=None,
            origin_code=None,
            meas_type_code=None,
            goods_nomenclature_exists=None,
            geographical_area_exists=None,
            measure_type_exists=None,
            measure_exists=None,
        ),
    ]


def test_report_name(eu_data_report):
    assert eu_data_report.name == "Table report of EU data"


def test_report_description(eu_data_report):
    assert (
        eu_data_report.description
        == "Imported data from the EU tariff using the upload CSV feature"
    )


def test_report_enabled(eu_data_report):
    assert eu_data_report.enabled


def test_report_headers(eu_data_report):
    expected_headers = [
        {"field": field, "filter": "agTextColumnFilter"}
        for field in [
            "Add code",
            "Duty",
            "End date",
            "Geographical area exists",
            "Goods code",
            "Goods nomenclature exists",
            "Legal base",
            "Meas type code",
            "Measure exists",
            "Measure type",
            "Measure type exists",
            "Order no",
            "Origin",
            "Origin code",
            "Red ind",
            "Start date",
        ]
    ]
    assert eu_data_report.headers() == expected_headers


@pytest.mark.parametrize(
    "mock_row, expected_row",
    [
        (
            EUDataModel(
                goods_code="123",
                add_code="456",
                order_no=None,
                start_date=None,
                end_date=None,
                red_ind=None,
                origin=None,
                measure_type=None,
                legal_base=None,
                duty=None,
                origin_code=None,
                meas_type_code=None,
                goods_nomenclature_exists=None,
                geographical_area_exists=None,
                measure_type_exists=None,
                measure_exists=None,
            ),
            {
                "Goods code": "123",
                "Add code": "456",
                "Duty": "None",
                "End date": "None",
                "Geographical area exists": "None",
                "Goods nomenclature exists": "None",
                "Legal base": "None",
                "Meas type code": "None",
                "Measure exists": "None",
                "Measure type": "None",
                "Measure type exists": "None",
                "Order no": "None",
                "Origin": "None",
                "Origin code": "None",
                "Red ind": "None",
                "Start date": "None",
            },
        ),
    ],
)
def test_report_row(eu_data_report, mock_row, expected_row):
    assert eu_data_report.row(mock_row) == expected_row


def test_report_rows(eu_data_report, mock_data):
    eu_data_report.query = lambda: mock_data
    expected_rows = [
        {
            "Goods code": "123",
            "Add code": "456",
            "Duty": "None",
            "End date": "None",
            "Geographical area exists": "None",
            "Goods nomenclature exists": "None",
            "Legal base": "None",
            "Meas type code": "None",
            "Measure exists": "None",
            "Measure type": "None",
            "Measure type exists": "None",
            "Order no": "None",
            "Origin": "None",
            "Origin code": "None",
            "Red ind": "None",
            "Start date": "None",
        },
        {
            "Add code": "012",
            "Duty": "None",
            "End date": "None",
            "Geographical area exists": "None",
            "Goods code": "789",
            "Goods nomenclature exists": "None",
            "Legal base": "None",
            "Meas type code": "None",
            "Measure exists": "None",
            "Measure type": "None",
            "Measure type exists": "None",
            "Order no": "None",
            "Origin": "None",
            "Origin code": "None",
            "Red ind": "None",
            "Start date": "None",
        },
    ]
    assert eu_data_report.rows() == expected_rows
