from datetime import date
from datetime import timedelta

import pytest

from commodities.models import GoodsNomenclature
from commodities.models.dc import CommodityCollectionLoader
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
            False,
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
                "additional_code": None,
            },
            True,
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
        "explicit:overlapping:no_additional_code",
        "explicit:overlapping:reduction",
        "implicit:not-overlapping",
        "explicit:not-overlapping",
        "deleted",
    ],
)
def related_measure_dates(request, date_ranges):
    get_measure_factory_properties, date_overlap = request.param
    return get_measure_factory_properties(date_ranges), date_overlap


@pytest.mark.parametrize(
    ("existing_code", "overlapping_code", "error_expected"),
    (
        (False, True, True),
        (True, False, True),
        (True, True, False),
        (False, False, False),
    ),
)
def test_ME16(existing_code, overlapping_code, error_expected):
    """Integrating a measure with an additional code when an equivalent or
    overlapping measures without additional code already exists and vice-versa,
    should be forbidden."""

    additional_code = factories.AdditionalCodeFactory.create()
    existing = factories.MeasureFactory.create(
        additional_code=(additional_code if existing_code else None),
    )
    measure = factories.MeasureFactory.create(
        measure_type=existing.measure_type,
        geographical_area=existing.geographical_area,
        goods_nomenclature=existing.goods_nomenclature,
        additional_code=(additional_code if overlapping_code else None),
        order_number=existing.order_number,
        reduction=existing.reduction,
    )
    with raises_if(BusinessRuleViolation, error_expected):
        business_rules.ME16(measure.transaction).validate(measure)


def create_goods_nomenclature_with_clashing_indents(source_goods_nomenclature):
    """
    Updates the source goods nomenclature indent to be 1, and creates a new
    goods nomenclature with multiple indents with the same start date but
    different indent values.

    This is used to create a known issue in tap where it will alternate between
    indents randomly and potentially present indents incorrectly (until fixed,
    currently WIP)
    """
    original = source_goods_nomenclature.indents.get()
    original.indent = 1
    original.save(force_write=True)

    good = factories.GoodsNomenclatureFactory.create(
        item_id=source_goods_nomenclature.item_id[:8] + "90",
        valid_between=source_goods_nomenclature.valid_between,
        indent__indent=source_goods_nomenclature.indents.first().indent + 1,
    )

    factories.GoodsNomenclatureIndentFactory.create(
        indented_goods_nomenclature=good,
        update_type=UpdateType.UPDATE,
        version_group=good.indents.first().version_group,
        validity_start=good.indents.first().validity_start,
        indent=source_goods_nomenclature.indents.first().indent - 1,
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
            create_goods_nomenclature_with_clashing_indents,
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
    create_goods_nomenclature_function, expected_result = request.param
    return (
        create_goods_nomenclature_function(existing_goods_nomenclature),
        expected_result,
    )


@pytest.fixture(
    params=(
        {"with_order_number": True},
        {"with_dead_order_number": True},
        {"with_additional_code": True},
        {},
    ),
    ids=[
        "with_order_number",
        "with_dead_order_number",
        "with_additional_code",
        "nothing",
    ],
)
def measure_instance_for_compile_query(request):
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


def test_ME16_part_2(related_measure_data):
    """
    Tests that another measure within the chapter with matching properties :
    measure type, geo area, order number and reduction indicator and the
    inverted absence of additional code raise exceptions correctly.

    (see ME16 business rule for more details)
    """

    related_data, error_expected = related_measure_data
    related = factories.MeasureFactory.create(**related_data)

    with raises_if(BusinessRuleViolation, error_expected):
        business_rules.ME16(related.transaction).validate(related)


def test_ME16_query_similar_measures(measure_instance_for_compile_query):
    """Test that the query_similar_measures method does check against  measure
    type, geo area, order number, additional code and reduction indicator."""

    measure = measure_instance_for_compile_query

    me16 = business_rules.ME16(measure.transaction)

    target = str(me16.query_similar_measures(measure))
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
        assert f"'additional_code__isnull', True" in target
    else:
        assert f"'additional_code__isnull', False" in target


def test_ME16_works_and_ignores_archived_measure_data(
    seed_database_with_indented_goods,
):
    # setup data with archived workbasket and published workbasket
    goods = GoodsNomenclature.objects.all().get(item_id="2903691900")
    commodities_collection = CommodityCollectionLoader(prefix="2903").load()

    archived_transaction = factories.TransactionFactory.create(archived=True)
    old_regulation = factories.RegulationFactory.create(
        valid_between=TaricDateRange(date(1982, 1, 1), date(1982, 12, 31)),
    )
    wonky_archived_measure = factories.MeasureFactory.create(
        transaction=archived_transaction,
        goods_nomenclature=goods,
        generating_regulation=old_regulation,
        terminating_regulation=old_regulation,
        valid_between=TaricDateRange(date.today() + timedelta(days=-100)),
    )

    draft_transaction = factories.TransactionFactory.create(draft=True)
    draft_measure = factories.MeasureFactory.create(
        goods_nomenclature=goods,
        valid_between=TaricDateRange(date.today() + timedelta(days=-100)),
    )

    rule = business_rules.ME16(draft_transaction)

    # if this fails, it will give amn out of range error
    result = rule.validate(draft_measure)

    assert result is None
    assert Measure.objects.all().count() == 2
    assert wonky_archived_measure.generating_regulation == old_regulation
