"""
Includes tests for commodity tree change scenarios outlined in ADR13.

Each scenario will cover at least one of two types of issues:
1. Guarantee that the tree hierarchy is correctly interpreted after the change
   - e.g. each comodity has the right parents, children, siblings, etc. post-change
2. Guarantee correct detection of, and remedy for, the side effects on objects related
   to the changed commodity as well as its hierarchy pre- and post-change
   - e.g. any measures or footnote associations that may be caught up in the change
     in a way that they now incidentally begin to violate business rules
"""

import pytest

from commodities.models.dc import CommodityChange
from commodities.tests.conftest import TScenario
from common.models.meta.wrappers import TrackedModelWrapper
from common.models.records import TrackedModel
from common.validators import UpdateType

pytestmark = pytest.mark.django_db


def validate_captured_side_effect(
    change: CommodityChange,
    obj: TrackedModel,
    update_type: UpdateType,
) -> None:
    key = TrackedModelWrapper(obj=obj).identifier

    assert key in change.side_effects
    assert change.side_effects[key].obj == obj
    assert change.side_effects[key].update_type == update_type


def test_scenario1_add_node_diff(scenario_1: TScenario):
    """Asserts correct handling of ADR 13, scenario 1."""
    collection, changes = scenario_1

    parent = collection.get_commodity("9999")
    sibling = collection.get_commodity("9999.10", "80")

    before = collection.current_snapshot
    collection.update(changes)
    after = collection.current_snapshot

    # Assert expected post-update tree hierarchy
    node = changes[0].candidate
    assert after.get_parent(node) == parent
    assert after.get_siblings(node) == [sibling]

    # Assert expected snapshot diffs
    diff = after.compare_siblings(sibling, before).diff
    assert diff == [node]
    diff = after.compare_children(parent, before).diff
    assert diff == [node]


def test_scenario2_delete_node(scenario_2: TScenario, date_ranges):
    """Asserts correct handling of ADR 13, scenario 2."""
    collection, changes = scenario_2

    parent = collection.get_commodity("9999")
    sibling = collection.get_commodity("9999.10", "80")

    before = collection.current_snapshot
    collection.update(changes)
    after = collection.current_snapshot

    node = changes[0].current

    # Assert expected post-update tree hierarchy
    assert node not in after.get_children(parent)
    assert node not in after.get_siblings(sibling)

    # Assert expected snapshot diffs
    diff = after.compare_siblings(sibling, before).diff
    assert diff == [node]
    diff = after.compare_children(parent, before).diff
    assert diff == [node]

    # Assert side-effects captured and BR-s violation pre-empted
    # NIG34 / NIG35
    change = changes[0]
    measure = change.current.obj.measures.first()
    validate_captured_side_effect(change, measure, UpdateType.DELETE)

    # Not covered by a BR
    association = change.current.obj.footnote_associations.first()
    validate_captured_side_effect(change, association, UpdateType.DELETE)


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
    collection, changes = scenario_4

    collection.update(changes)

    # Assert side-effects captured and BR-s violation pre-empted
    change = changes[0]

    # NIG22
    associations = change.candidate.obj.footnote_associations.order_by("id")

    # Case 1 - association that still overlaps with the good's new validity span
    # It should be picked up in side effects with a flag UPDATE
    association = associations.first()
    validate_captured_side_effect(change, association, UpdateType.UPDATE)

    # Case 2 - association that no longer overlaps with the good's new validity span
    # It should be picked up in side effects with a flag DELETE
    association = associations.last()
    validate_captured_side_effect(change, association, UpdateType.DELETE)

    # NIG30 / NIG31
    measures = change.candidate.obj.dependent_measures.order_by("id")

    # Case 1 - measure that still overlaps with the good's new validity span
    # It should be picked up in side effects with a flag UPDATE
    measure = measures.first()
    validate_captured_side_effect(change, measure, UpdateType.UPDATE)

    # Case 2 - measure that no longer overlaps with the good's new validity span
    # It should be picked up in side effects with a flag DELETE
    measure = measures.last()
    validate_captured_side_effect(change, measure, UpdateType.DELETE)


def test_scenario5_intermediate_suffix(scenario_5: TScenario):
    """Asserts correct handling of ADR 13, scenario 5."""
    collection, changes = scenario_5
    collection.update(changes)

    # Assert expected post-update tree hierarchy
    snapshot = collection.current_snapshot
    parent = snapshot.get_commodity("9999.20", "20")

    assert parent is not None
    assert not snapshot.is_declarable(parent)

    # Assert side-effects captured and BR-s violation pre-empted
    change = changes[1]

    # ME7
    measure = change.candidate.obj.dependent_measures.first()
    validate_captured_side_effect(change, measure, UpdateType.DELETE)


def test_scenario6_increase_indent(scenario_6: TScenario):
    """Asserts correct handling of ADR 13, scenario 6."""
    # TODO: Extend to cover ME32, ME71, ME88, and NIG18
    collection, changes = scenario_6
    collection.update(changes)

    # Assert expected post-update tree hierarchy
    snapshot = collection.current_snapshot
    commodity = collection.get_commodity("9999.20.10")
    parent = snapshot.get_parent(commodity)

    assert parent == collection.get_commodity("9999.10")

    # Assert side-effects captured and BR-s violation pre-empted
    change = changes[0]

    # ME88
    measure = change.candidate.obj.measures.first()
    validate_captured_side_effect(change, measure, UpdateType.DELETE)


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
