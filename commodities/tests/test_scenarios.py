import pytest

from .conftest import TScenario

pytestmark = pytest.mark.django_db


def test_scenario1_add_node(scenario_1: TScenario):
    """Asserts correct handling of ADR 13, scenario 1."""
    collection, changes = scenario_1

    parent = collection.get_commodity("9999")
    sibling = collection.get_commodity("9999.10", "80")

    before = collection.current_snapshot
    collection.update(changes)
    after = collection.current_snapshot

    node = changes[0].candidate
    assert after.get_parent(node) == parent
    assert after.get_siblings(node) == [sibling]

    diff = after.compare_siblings(sibling, before).diff
    assert diff == [node]

    diff = after.compare_children(parent, before).diff
    assert diff == [node]


def test_scenario2_delete_node(scenario_2: TScenario):
    """Asserts correct handling of ADR 13, scenario 2."""
    # TODO: Extend to cover NIG34 and NIG35 for the deleted node
    collection, changes = scenario_2

    parent = collection.get_commodity("9999")
    sibling = collection.get_commodity("9999.10", "80")

    before = collection.current_snapshot
    collection.update(changes)
    after = collection.current_snapshot

    node = changes[0].current

    assert node not in after.get_children(parent)
    assert node not in after.get_siblings(sibling)

    diff = after.compare_siblings(sibling, before).diff
    assert diff == [node]

    diff = after.compare_children(parent, before).diff
    assert diff == [node]


def test_scenario3_orphaned_node(scenario_3: TScenario):
    """Asserts correct handling of ADR 13, scenario 3."""
    # TODO: Extend to cover ME32 for the orphan and the new parent
    collection, changes = scenario_3

    child = collection.get_commodity("9999.20.00.10")
    before = collection.current_snapshot
    collection.update(changes)
    after = collection.current_snapshot

    assert before.get_parent(child) == before.get_commodity("9999.20")
    assert after.get_parent(child) == after.get_commodity("9999.10")


def test_scenario4_change_time_span(scenario_4: TScenario):
    """Asserts correct handling of ADR 13, scenario 4."""
    # TODO: Extend test to cover NIG22, NIG30, and NIG31 on the updated node
    collection, changes = scenario_4


def test_scenario5_intermediate_suffix(scenario_5: TScenario):
    """Asserts correct handling of ADR 13, scenario 5."""
    # TODO: Extend to cover ME7 on the new parent with intermediate suffix
    collection, changes = scenario_5

    collection.update(changes)
    snapshot = collection.current_snapshot
    parent = snapshot.get_commodity("9999.20", "20")

    assert parent is not None
    assert snapshot.is_declarable(parent) == False


def test_scenario6_increase_indent(scenario_6: TScenario):
    """Asserts correct handling of ADR 13, scenario 6."""
    # TODO: Extend to cover ME32, ME71, ME88, and NIG18
    collection, changes = scenario_6

    collection.update(changes)
    snapshot = collection.current_snapshot

    commodity = collection.get_commodity("9999.20")
    parent = snapshot.get_parent(commodity)

    assert parent == collection.get_commodity("9999.10")


def test_scenario7_increase_indent_orphan_node(scenario_7: TScenario):
    """Asserts correct handling of ADR 13, scenario 7."""
    # TODO: Extend to cover ME32, ME71, ME88, and NIG18
    collection, changes = scenario_7

    collection.update(changes)
    snapshot = collection.current_snapshot

    commodity = collection.get_commodity("9999.20.00.10")
    parent = snapshot.get_parent(commodity)

    assert parent == collection.get_commodity("9999.10")


def test_scenario8_increase_indent_orphan_node(scenario_8: TScenario):
    """Asserts correct handling of ADR 13, scenario 8."""
    # TODO: Extend to cover ME32, ME71, ME88, and NIG18
    collection, changes = scenario_8

    collection.update(changes)
    snapshot = collection.current_snapshot

    commodity = collection.get_commodity("9999.20.00.10")
    parent = snapshot.get_parent(commodity)

    assert parent == collection.get_commodity("9999.20")
