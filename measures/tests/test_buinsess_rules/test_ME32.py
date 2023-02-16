import pytest

from common.business_rules import BusinessRuleViolation
from common.tests import factories
from common.tests.util import Dates
from common.tests.util import raises_if
from common.validators import UpdateType
from measures import business_rules

pytestmark = pytest.mark.django_db


@pytest.fixture(
    params=(
        (
            lambda d: {
                "valid_between": d.overlap_normal_earlier,
            },
            True,
        ),
        (
            lambda d: {
                "valid_between": d.overlap_normal_earlier,
                "measure_type": factories.MeasureTypeFactory.create(),
            },
            False,
        ),
        (
            lambda d: {
                "valid_between": d.overlap_normal_earlier,
                "geographical_area": factories.GeographicalAreaFactory.create(),
            },
            False,
        ),
        (
            lambda d: {
                "valid_between": d.overlap_normal_earlier,
                "order_number": factories.QuotaOrderNumberFactory.create(),
            },
            False,
        ),
        (
            lambda d: {
                "valid_between": d.overlap_normal_earlier,
                "additional_code": factories.AdditionalCodeFactory.create(),
            },
            False,
        ),
        (
            lambda d: {
                "valid_between": d.overlap_normal_earlier,
                "reduction": None,
            },
            False,
        ),
        (
            lambda d: {
                "valid_between": Dates.no_end_before(d.adjacent_earlier.lower),
                "generating_regulation__valid_between": d.adjacent_earlier,
                "generating_regulation__effective_end_date": d.adjacent_earlier.upper,
            },
            False,
        ),
        (
            lambda d: {
                "valid_between": d.later,
            },
            False,
        ),
        (
            lambda d: {
                "valid_between": d.overlap_normal_earlier,
                "update_type": UpdateType.DELETE,
            },
            False,
        ),
    ),
    ids=[
        "explicit:overlapping",
        "explicit:overlapping:measure_type",
        "explicit:overlapping:geographical_area",
        "explicit:overlapping:order_number",
        "explicit:overlapping:additional_code",
        "explicit:overlapping:reduction",
        "implicit:not-overlapping",
        "explicit:not-overlapping",
        "deleted",
    ],
)
def related_measure_dates(request, date_ranges):
    callable, date_overlap = request.param
    return callable(date_ranges), date_overlap


def updated_goods_nomenclature(e):
    original = e.indents.get()
    original.indent = 1
    original.save(force_write=True)

    good = factories.GoodsNomenclatureFactory.create(
        item_id=e.item_id[:8] + "90",
        valid_between=e.valid_between,
        indent__indent=e.indents.first().indent + 1,
    )

    factories.GoodsNomenclatureIndentFactory.create(
        indented_goods_nomenclature=good,
        update_type=UpdateType.UPDATE,
        version_group=good.indents.first().version_group,
        validity_start=good.indents.first().validity_start,
        indent=e.indents.first().indent - 1,
    )

    return good



@pytest.fixture(
    params=(
        (lambda e: e, True),
        (
            lambda e: factories.GoodsNomenclatureFactory.create(
                item_id=e.item_id[:8] + "90",
                valid_between=e.valid_between,
            ),
            True,
        ),
        (
            updated_goods_nomenclature,
            False,
        ),
    ),
    ids=[
        "current:self",
        "current:child",
        "former:parent",
    ],
)
def related_goods_nomenclature(request, existing_goods_nomenclature):
    callable, expected = request.param
    return callable(existing_goods_nomenclature), expected


@pytest.fixture
def related_measure_data(
    related_measure_dates,
    related_goods_nomenclature,
    existing_measure,
):
    nomenclature, nomenclature_overlap = related_goods_nomenclature
    validity_data, date_overlap = related_measure_dates
    existing_measure, overlaps_normal = existing_measure
    full_data = {
        "goods_nomenclature": nomenclature,
        "measure_type": existing_measure.measure_type,
        "geographical_area": existing_measure.geographical_area,
        "order_number": existing_measure.order_number,
        "additional_code": existing_measure.additional_code,
        "reduction": existing_measure.reduction,
        "transaction": existing_measure.transaction.workbasket.new_transaction(),
        **validity_data,
    }
    error_expected = date_overlap and nomenclature_overlap and overlaps_normal

    return full_data, error_expected


def test_ME32(related_measure_data):
    """
    There may be no overlap in time with other measure occurrences with a goods
    code in the same nomenclature hierarchy which references the same measure
    type, geo area, order number, additional code and reduction indicator. This
    rule is not applicable for Meursing additional codes.

    This is an extension of the previously described ME1 to all commodity codes
    in the upward hierarchy and all commodity codes in the downward hierarchy.
    """

    related_data, error_expected = related_measure_data
    related = factories.MeasureFactory.create(**related_data)

    with raises_if(BusinessRuleViolation, error_expected):
        business_rules.ME32(related.transaction).validate(related)

