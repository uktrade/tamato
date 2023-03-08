import datetime

import factory
import openpyxl
import pytest

from common.tests import factories
from common.tests.util import assert_many_records_match
from measures.sheet_importers import MeasureSheetRow
from measures.sheet_importers import process_date_value
from measures.tests.factories import MeasureSheetRowFactory

pytestmark = pytest.mark.django_db


@pytest.fixture(
    params=(
        [],
        [{}],
        [{}] * 10,
        [{"order_number": factory.SubFactory(factories.QuotaOrderNumberFactory)}],
        [{"dead_order_number": factories.QuotaOrderNumberFactory.order_number}],
        [{"additional_code": factory.SubFactory(factories.AdditionalCodeFactory)}],
        [{"dead_additional_code": factories.string_sequence(length=4)}],
        [{"valid_between": factories.date_ranges("normal")}],
        [{"with_footnote": True}],
        [{"with_exclusion": True}],
        [
            {
                "with_condition": True,
                "condition__condition_code__code": "B",
                "condition__duty_amount": None,
                "condition__monetary_unit": None,
            },
        ],
    ),
    ids=(
        "empty",
        "one_measure",
        "multiple_measures",
        "with_quota",
        "with_missing_quota",
        "with_additional_code",
        "with_missing_additional_code",
        "with_end_date",
        "with_footnotes",
        "with_exclusions",
        "with_conditions",
    ),
)
def measures(request, duty_expressions):
    with factories.SimpleQueuedWorkBasketFactory.create().new_transaction():
        return [
            factories.MeasureFactory.create(**k, reduction=None) for k in request.param
        ]


@pytest.fixture
def measure_rows(measures):
    return [MeasureSheetRowFactory.create(measure=k) for k in measures]


@pytest.fixture
def measure_worksheet(measure_rows):
    """Provides an Excel worksheet object containing a header row and the
    supplied measure rows."""
    workbook = openpyxl.Workbook()
    worksheet = workbook.active

    worksheet.append(MeasureSheetRow.columns)
    for row in measure_rows:
        worksheet.append(row)

    return worksheet


def test_measure_sheet_importer(measure_worksheet, measures):
    workbasket = factories.WorkBasketFactory.create()
    imported_measures = list(
        MeasureSheetRow.import_sheet(measure_worksheet, workbasket),
    )
    assert_many_records_match(
        measures,
        imported_measures,
        ignore={"sid", "export_refund_nomenclature_sid"},
    )
    for imported_measure, measure in zip(imported_measures, measures):
        assert_many_records_match(
            measure.footnotes.all(),
            imported_measure.footnotes.all(),
        )
        assert_many_records_match(
            measure.exclusions.all(),
            imported_measure.exclusions.all(),
            ignore={"modified_measure"},
        )
        assert_many_records_match(
            measure.conditions.all(),
            imported_measure.conditions.all(),
            ignore={"sid", "component_sequence_number", "dependent_measure"},
        )


@pytest.mark.parametrize(
    "value",
    (
        datetime.date.today(),
        datetime.datetime.now(),
    ),
    ids=(
        "date",
        "datetime",
    ),
)
def test_process_date_value(value):
    d = process_date_value(value)
    assert type(d) == datetime.date
