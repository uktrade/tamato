import pytest

from commodities.models import GoodsNomenclature
from common.tests.factories import GoodsNomenclatureFactory
from common.tests.factories import GoodsNomenclatureIndentNodeFactory
from common.tests.util import Dates
from importer.management.commands.utils import convert_eur_to_gbp
from importer.management.commands.utils import NomenclatureTreeCollector
from importer.management.commands.utils import parse_trade_remedies_duty_expression

pytestmark = pytest.mark.django_db


def make_child(parent: GoodsNomenclature, **kwargs) -> GoodsNomenclature:
    g = GoodsNomenclatureFactory(indent__node=None, **kwargs)
    data = GoodsNomenclatureIndentNodeFactory.stub(
        indent=g.indents.get(),
    ).__dict__
    parent.indents.get().nodes.get().add_child(**data)
    return g


@pytest.fixture
def root_cc() -> GoodsNomenclature:
    return GoodsNomenclatureFactory(item_id="8600000000", suffix="80")


@pytest.fixture
def child_cc(root_cc: GoodsNomenclature) -> GoodsNomenclature:
    return make_child(root_cc, item_id="8610000000", suffix="80")


@pytest.fixture
def sibling_cc(root_cc: GoodsNomenclature) -> GoodsNomenclature:
    return make_child(root_cc, item_id="8620000000", suffix="80")


@pytest.fixture
def grandchild_cc(child_cc: GoodsNomenclature) -> GoodsNomenclature:
    return make_child(child_cc, item_id="8610000010", suffix="80")


@pytest.fixture
def indepedent_root_cc() -> GoodsNomenclature:
    return GoodsNomenclatureFactory(item_id="0100000000", suffix="80")


@pytest.fixture
def phantom_root_cc() -> GoodsNomenclature:
    return GoodsNomenclatureFactory(item_id="0200000000", suffix="10")


@pytest.fixture
def child_of_phantom_cc(phantom_root_cc: GoodsNomenclature) -> GoodsNomenclature:
    return make_child(phantom_root_cc, item_id="0201000000", suffix="80")


@pytest.fixture
def working_set(date_ranges: Dates) -> NomenclatureTreeCollector[int]:
    return NomenclatureTreeCollector[int](date=date_ranges.now)


def test_single_root(
    root_cc: GoodsNomenclature,
    working_set: NomenclatureTreeCollector[int],
):
    """The nomenclature collector should be able to remember an item of context
    whenever a CC is added."""
    working_set.add(root_cc, 100)
    buffer = list(working_set.buffer())
    assert len(buffer) == 1
    assert buffer[0][0] == root_cc
    assert buffer[0][1] == 100


def test_different_subtrees(
    working_set: NomenclatureTreeCollector[int],
    root_cc: GoodsNomenclature,
    indepedent_root_cc: GoodsNomenclature,
):
    """When a CC from a different subtree (i.e. not a descendant of the first
    node that was added) is added, it should not be added to the buffer and instead
    add() should return False. This is so that external code can detect the fact
    that we have reached a commodity code that is not part of the current set."""
    working_set.add(root_cc, 100)
    result = working_set.add(indepedent_root_cc, 200)
    buffer = list(working_set.buffer())
    assert result == False
    assert len(buffer) == 1
    assert buffer[0][0] == root_cc
    assert buffer[0][1] == 100


def test_child(
    working_set: NomenclatureTreeCollector[int],
    root_cc: GoodsNomenclature,
    child_cc: GoodsNomenclature,
):
    """When we add a descendant CC, the root should be split into its children.
    As this root only has one child, this means that the root is no longer
    present and only the child remains."""
    working_set.add(root_cc, 100)
    result = working_set.add(child_cc, 200)
    buffer = list(working_set.buffer())
    assert result == True
    assert buffer[0][0] == child_cc, buffer
    assert buffer[0][1] == 200


def test_no_overlaps(
    working_set: NomenclatureTreeCollector[int],
    root_cc: GoodsNomenclature,
    child_cc: GoodsNomenclature,
    sibling_cc: GoodsNomenclature,
):
    """When a child and sibling are added, there should be no overlaps in the
    resulting buffer – i.e. only the child and the sibling are present."""
    working_set.add(root_cc, 100)
    working_set.add(child_cc, 200)
    working_set.add(sibling_cc, 300)
    buffer = list(working_set.buffer())
    assert len(buffer) == 2
    assert buffer[0][0] == child_cc
    assert buffer[0][1] == 200
    assert buffer[1][0] == sibling_cc
    assert buffer[1][1] == 300


def test_far_descendents(
    working_set: NomenclatureTreeCollector[int],
    root_cc: GoodsNomenclature,
    sibling_cc: GoodsNomenclature,
    grandchild_cc: GoodsNomenclature,
):
    """When a grandchild is added, the hierarchy should be split down to contain
    that grandchild. This means the root is split and then the child is also
    split. Note that the sibling inherits its context object from the root
    because it has not been added to the tree explicitly."""
    working_set.add(root_cc, 100)
    working_set.add(grandchild_cc, 200)
    buffer = list(working_set.buffer())
    assert len(buffer) == 2, f"len(buffer) = {len(buffer)}"
    assert buffer[0][0] == grandchild_cc, f"buffer[0][0] = {buffer[0][0]}"
    assert buffer[0][1] == 200, f"buffer[0][1] = {buffer[0][1]}"
    assert buffer[1][0] == sibling_cc
    assert buffer[1][1] == 100


def test_splits_phantom_headings(
    working_set: NomenclatureTreeCollector[int],
    phantom_root_cc: GoodsNomenclature,
    child_of_phantom_cc: GoodsNomenclature,
):
    """When a heading is added that does not have suffix 80, it should be split
    immediately. Only codes with suffix 80 should be returned by the collector.
    This is to avoid ME7 errors."""
    working_set.add(phantom_root_cc, 100)
    buffer = list(working_set.buffer())
    assert len(buffer) == 1
    assert buffer[0][0] == child_of_phantom_cc
    assert buffer[0][1] == 100


def test_explicit_overrides_implicit_context(
    working_set: NomenclatureTreeCollector[int],
    root_cc: GoodsNomenclature,
    sibling_cc: GoodsNomenclature,
    grandchild_cc: GoodsNomenclature,
):
    """When a node is split into its child nodes, if those child nodes are
    subsequently added to the tree, they should retain the context that they
    were added with rather than the context of their old parent."""
    working_set.add(root_cc, 100)
    working_set.add(grandchild_cc, 200)
    working_set.add(sibling_cc, 300)
    buffer = list(working_set.buffer())
    assert len(buffer) == 2
    assert buffer[0][0] == grandchild_cc
    assert buffer[0][1] == 200
    assert buffer[1][0] == sibling_cc
    assert buffer[1][1] == 300


def test_same_cc_overrides_original_context(
    working_set: NomenclatureTreeCollector[int],
    root_cc: GoodsNomenclature,
):
    """When a node is added to the tree having already been added before, it
    should retain the new context rather than hold on to the old one."""
    working_set.add(root_cc, 100)
    working_set.add(root_cc, 200)
    buffer = list(working_set.buffer())
    assert len(buffer) == 1
    assert buffer[0][0] == root_cc
    assert buffer[0][1] == 200


def test_parse_duty_expression():

    expression = parse_trade_remedies_duty_expression(
        "Cond: A cert: D-008 (01):0.000 EUR TNE I ; A (01):172.200 EUR TNE I"
    )

    assert expression[0].condition.condition_code == "A"
    assert expression[0].condition.certificate is True
    assert expression[0].condition.certificate_type_code == "D"
    assert expression[0].condition.certificate_code == "008"
    assert expression[0].condition.action_code == "01"

    assert expression[0].component.duty_expression_id == "01"
    assert expression[0].component.duty_amount == "0.000"
    assert expression[0].component.monetary_unit_code == "EUR"
    assert expression[0].component.measurement_unit_code == "TNE"
    assert expression[0].component.measurement_unit_qualifier_code == "I"

    assert expression[1].condition.condition_code == "A"
    assert expression[1].condition.certificate is False
    assert expression[1].condition.certificate_type_code is None
    assert expression[1].condition.certificate_code is None
    assert expression[1].condition.action_code == "01"

    assert expression[1].component.duty_expression_id == "01"
    assert expression[1].component.duty_amount == "172.200"
    assert expression[1].component.monetary_unit_code == "EUR"
    assert expression[1].component.measurement_unit_code == "TNE"
    assert expression[1].component.measurement_unit_qualifier_code == "I"

    expression = parse_trade_remedies_duty_expression(
        "Cond: A cert: D-017 (01):0.000 % ; A cert: D-018 (01):28.200 % ; A (01):28.200 %"
    )

    assert expression[0].condition.condition_code == "A"
    assert expression[0].condition.certificate is True
    assert expression[0].condition.certificate_type_code == "D"
    assert expression[0].condition.certificate_code == "017"
    assert expression[0].condition.action_code == "01"

    assert expression[0].component.duty_expression_id == "01"
    assert expression[0].component.duty_amount == "0.000"
    assert expression[0].component.monetary_unit_code == "%"
    assert expression[0].component.measurement_unit_code is None
    assert expression[0].component.measurement_unit_qualifier_code is None

    assert expression[1].condition.condition_code == "A"
    assert expression[1].condition.certificate is True
    assert expression[1].condition.certificate_type_code == "D"
    assert expression[1].condition.certificate_code == "018"
    assert expression[1].condition.action_code == "01"

    assert expression[1].component.duty_expression_id == "01"
    assert expression[1].component.duty_amount == "28.200"
    assert expression[1].component.monetary_unit_code == "%"
    assert expression[1].component.measurement_unit_code is None
    assert expression[1].component.measurement_unit_qualifier_code is None

    assert expression[2].condition.condition_code == "A"
    assert expression[2].condition.certificate is False
    assert expression[2].condition.certificate_type_code is None
    assert expression[2].condition.certificate_code is None
    assert expression[2].condition.action_code == "01"

    assert expression[2].component.duty_expression_id == "01"
    assert expression[2].component.duty_amount == "28.200"
    assert expression[2].component.monetary_unit_code == "%"
    assert expression[2].component.measurement_unit_code is None
    assert expression[2].component.measurement_unit_qualifier_code is None


def test_parse_duty_expression_with_conversion():
    expression = parse_trade_remedies_duty_expression(
        "Cond: A cert: D-017 (01):10.000 EUR", eur_gbp_conversion_rate=2
    )

    assert expression[0].component.duty_amount == "20.000"
    assert expression[0].component.monetary_unit_code == "GBP"

    expression = parse_trade_remedies_duty_expression(
        "Cond: A cert: D-017 (01):10.000 USD", eur_gbp_conversion_rate=2
    )

    assert expression[0].component.duty_amount == "10.000"
    assert expression[0].component.monetary_unit_code == "USD"


def test_parse_duty_expression_with_nihil():
    expression = parse_trade_remedies_duty_expression("Cond: A cert: D-017 (01):NIHIL")

    assert not expression[0].condition
    assert expression[0].component.duty_expression_id == 37

    expression = parse_trade_remedies_duty_expression("NIHIL")

    assert not expression[0].condition
    assert expression[0].component.duty_expression_id == 37


def test_parse_duty_expression_with_no_condition():
    expression = parse_trade_remedies_duty_expression("172.200 EUR TNE I ")

    assert not expression[0].condition
    assert expression[0].component.duty_expression_id == "01"
    assert expression[0].component.duty_amount == "172.200"
    assert expression[0].component.monetary_unit_code == "EUR"
    assert expression[0].component.measurement_unit_code == "TNE"
    assert expression[0].component.measurement_unit_qualifier_code == "I"


def test_parse_duty_expression_with_nihil():
    expression = parse_trade_remedies_duty_expression("Cond: A cert: D-017 (01):NIHIL")

    assert expression[0].condition.condition_code == "A"
    assert expression[0].condition.certificate is True
    assert expression[0].condition.certificate_type_code == "D"
    assert expression[0].condition.certificate_code == "017"
    assert expression[0].condition.action_code == "01"

    assert expression[0].component.duty_expression_id == "37"
    assert expression[0].component.duty_amount is None
    assert expression[0].component.monetary_unit_code is None
    assert expression[0].component.measurement_unit_code is None
    assert expression[0].component.measurement_unit_qualifier_code is None

    expression = parse_trade_remedies_duty_expression("NIHIL")

    assert expression[0].condition is None
    assert expression[0].component.duty_expression_id == "37"
    assert expression[0].component.duty_amount is None
    assert expression[0].component.monetary_unit_code is None
    assert expression[0].component.measurement_unit_code is None
    assert expression[0].component.measurement_unit_qualifier_code is None


def test_eur_to_gbp_conversion():
    assert convert_eur_to_gbp("20.000", conversion_rate=2) == "40.000"
    assert convert_eur_to_gbp("1.000", conversion_rate=0.83687) == "0.830"
