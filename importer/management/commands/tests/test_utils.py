import pytest

from commodities.models import GoodsNomenclature
from common.tests.factories import GoodsNomenclatureFactory
from common.tests.factories import GoodsNomenclatureIndentNodeFactory
from common.tests.util import Dates
from importer.management.commands.utils import NomenclatureTreeCollector

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
