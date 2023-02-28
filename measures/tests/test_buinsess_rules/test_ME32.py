from datetime import date, timedelta

import pytest

from commodities.models import GoodsNomenclature
from commodities.models.dc import CommodityCollectionLoader, CommodityTreeSnapshot, SnapshotMoment
from common.business_rules import BusinessRuleViolation
from common.tests import factories
from common.tests.util import Dates
from common.tests.util import raises_if
from common.util import TaricDateRange
from common.validators import UpdateType
from measures import business_rules
from measures.models import Measure

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


@pytest.fixture(
    params=(
            {'with_order_number': True},
            {'with_dead_order_number': True},
            {'with_additional_code': True},
            {'with_dead_additional_code': True},
            {},
    ),
    ids=[
        "with_order_number",
        "with_dead_order_number",
        "with_additional_code",
        "with_dead_additional_code",
        "nothing",
    ],
)
def measure_data_for_compile_query(request):
    return factories.MeasureFactory.create(**request.param)


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


def test_ME32_compile_query(measure_data_for_compile_query):
    """
    Test that the compile_query method does check against  measure
    type, geo area, order number, additional code and reduction indicator.
    """

    measure = measure_data_for_compile_query

    me32 = business_rules.ME32(measure.transaction)
    # e.g. "(AND: ('geographical_area__sid', 1), ('measure_type__sid', '000'), ('reduction', 1), ('order_number__sid', 1), ('additional_code__sid', 1))"

    target = str(me32.compile_query(measure))
    assert f"'measure_type__sid', '{measure.measure_type.sid}'" in target
    assert f"'geographical_area__sid', {measure.geographical_area.sid}" in target

    assert f"'reduction', {measure.reduction}" in target

    if measure.order_number:
        assert f"'order_number__sid', {measure.order_number.sid}" in target
    else:
        assert f"'order_number__isnull', True" in target
        if measure.dead_order_number:
            assert f"'dead_order_number__sid', {measure.order_number.sid}" in target
        else:
            assert f"'dead_order_number__isnull', True" in target

    if measure.additional_code:
        assert f"'additional_code__sid', {measure.additional_code.sid}" in target
    else:
        if measure.dead_additional_code:
            assert f"'dead_additional_code', 'AAAA'" in target
        else:
            assert f"'dead_additional_code__isnull', True" in target
            assert f"'additional_code__isnull', True" in target


def test_ME32_works_with_wonky_archived_measure(seed_database_with_indented_goods):
    # setup data with archived workbasket and published workbasket
    goods = GoodsNomenclature.objects.all().get(item_id="2903691900")
    commodities_collection = CommodityCollectionLoader(prefix='2903').load()

    archived_transaction = factories.TransactionFactory.create(archived=True)
    old_regulation = factories.RegulationFactory.create(
        valid_between=TaricDateRange(date(1982, 1, 1), date(1982, 12, 31))
    )
    wonky_archived_measure = factories.MeasureFactory.create(
        transaction=archived_transaction,
        goods_nomenclature=goods,
        generating_regulation=old_regulation,
        terminating_regulation=old_regulation,
        valid_between=TaricDateRange(date.today() + timedelta(days=-100))
    )

    draft_transaction = factories.TransactionFactory.create(draft=True)
    draft_measure = factories.MeasureFactory.create(
        goods_nomenclature=goods,
        valid_between=TaricDateRange(date.today() + timedelta(days=-100))
    )

    rule = business_rules.ME32(draft_transaction)

    # if this fails, it will give amn out of range error
    result = rule.validate(draft_measure)

    assert result is None
    assert Measure.objects.all().count() == 2
    assert wonky_archived_measure.generating_regulation == old_regulation
