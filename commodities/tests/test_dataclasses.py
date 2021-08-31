from datetime import date
from datetime import timedelta

import pytest

from commodities.models.dc import CommodityChange
from common.validators import UpdateType
from conftest import not_raises

from .conftest import copy_commodity

pytestmark = pytest.mark.django_db


def verify_snapshot_members(collection, snapshot, excluded_date_ranges):
    excluded = [
        commodity
        for commodity in collection.commodities
        if commodity.obj.valid_between in excluded_date_ranges
    ]

    included = [
        commodity for commodity in collection.commodities if commodity not in excluded
    ]

    for commodity in excluded:
        assert commodity not in snapshot.commodities

    for commodity in included:
        assert commodity in snapshot.commodities


def test_commodity_dot_code(collection_full):
    c = collection_full.get_commodity("9999")
    assert c.dot_code == "9999.00.00.00"


def test_commodity_trimmed_code(collection_full):
    c_9999 = collection_full.get_commodity("9999")
    c_999920 = collection_full.get_commodity("999920")
    c_9999200010 = collection_full.get_commodity("9999200010")

    assert c_9999.trimmed_code == "9999"
    assert c_999920.trimmed_code == "999920"
    assert c_9999200010.trimmed_code == c_9999200010.code


def test_commodity_trimmed_dot_code(collection_full):
    c_999920 = collection_full.get_commodity("999920")
    c_9999200010 = collection_full.get_commodity("9999200010")

    assert c_999920.trimmed_dot_code == "9999.20"
    assert c_9999200010.trimmed_dot_code == c_9999200010.dot_code


def test_commodity_is_chapter(collection_full):
    c_99 = collection_full.get_commodity("99")
    c_9999 = collection_full.get_commodity("9999")

    assert c_99.is_chapter is True
    assert c_9999.is_chapter is False


def test_commodity_is_heading(collection_full):
    c_99 = collection_full.get_commodity("99")
    c_9999 = collection_full.get_commodity("9999")
    c_999910 = collection_full.get_commodity("999910")

    assert c_99.is_heading is False
    assert c_9999.is_heading is True
    assert c_999910.is_heading is False


def test_commodity_is_subheading(collection_full):
    c_9999 = collection_full.get_commodity("9999")
    c_999910 = collection_full.get_commodity("999910")
    c_9999200010 = collection_full.get_commodity("9999200010")

    assert c_9999.is_subheading is False
    assert c_999910.is_subheading is True
    assert c_9999200010.is_subheading is False


def test_collection_get_commodity(collection_full, commodities):
    for commodity in commodities.values():
        codes = [
            commodity.code,
            commodity.dot_code,
            commodity.trimmed_code,
            commodity.trimmed_dot_code,
        ]

        for code in codes:
            assert (
                collection_full.get_commodity(
                    code,
                    commodity.suffix,
                )
                == commodity
            )


@pytest.mark.parametrize(
    "case",
    [
        dict(
            delta=0,  # case: the tree snapshot for today
            excluded_range_names=[
                "adjacent",  # goes into effect tomorrow
                "adjacent_earlier",  # no longer in effect as of today
                "overlap_normal",  # goes into effect 15 days in the future
                "future",  # goes into effect 10 weeks in the future
            ],
        ),
        dict(
            delta=-1,  # case: the tree snapshot for yesterday
            excluded_range_names=[
                "normal",  # goes into effect today
                "no_end",  # goes into effect today
                "adjacent",  # goes into effect tomorrow
                "overlap_normal",  # goes into effect 15 days in the future
                "future",  # goes into effect 10 weeks in the future
            ],
        ),
        dict(
            delta=+15,  # case: the tree snapshot for the date 15 days from now
            excluded_range_names=[
                "adjacent_earlier",  # no longer in effect as of today
                "overlap_normal_earlier",  # no longer in effect as of the case date
                "future",  # goes into effect 8 weeks after the case date
            ],
        ),
    ],
)
def test_collection_get_calendar_clock_snapshot(collection_spanned, date_ranges, case):
    snapshot_date = date.today() + timedelta(days=case["delta"])
    snapshot = collection_spanned.get_calendar_clock_snapshot(snapshot_date)

    excluded_date_ranges = [
        getattr(date_ranges, range_name) for range_name in case["excluded_range_names"]
    ]
    verify_snapshot_members(
        collection_spanned,
        snapshot,
        excluded_date_ranges,
    )


def test_snapshot_get_parent(collection_basic):
    snapshot = collection_basic.current_snapshot

    c_9999 = snapshot.get_commodity("9999")
    c_999910 = snapshot.get_commodity("9999.10")

    assert snapshot.get_parent(c_999910) == c_9999


def test_snapshot_get_sibling(collection_basic):
    snapshot = collection_basic.current_snapshot

    c_999910 = snapshot.get_commodity("9999.10")
    c_999920 = snapshot.get_commodity("9999.20")

    assert snapshot.get_siblings(c_999910) == [c_999920]


def test_snapshot_get_children(collection_basic):
    snapshot = collection_basic.current_snapshot

    c_9999 = snapshot.get_commodity("9999")
    c_999910 = snapshot.get_commodity("9999.10")
    c_999920 = snapshot.get_commodity("9999.20")

    assert snapshot.get_children(c_9999) == [c_999910, c_999920]


def test_snapshot_get_parent_heading_zero_indent(collection_heading):
    snapshot = collection_heading.current_snapshot

    c_99 = snapshot.get_commodity("99")
    c_9910 = snapshot.get_commodity("9910")

    assert snapshot.get_parent(c_9910) == c_99


def test_snapshot_get_parent_suffixes_indents(collection_suffixes_indents):
    snapshot = collection_suffixes_indents.current_snapshot

    c_991010_10 = snapshot.get_commodity("9910.10", "10")
    c_991010_80 = snapshot.get_commodity("9910.10")
    c_991020 = snapshot.get_commodity("9910.20")

    assert snapshot.get_parent(c_991010_80) == c_991010_10
    assert snapshot.get_parent(c_991020) == c_991010_10


def test_snapshot_get_sibling_suffixes_indents(collection_suffixes_indents):
    snapshot = collection_suffixes_indents.current_snapshot

    c_991010_80 = snapshot.get_commodity("9910.10")
    c_991020 = snapshot.get_commodity("9910.20")

    siblings = snapshot.get_siblings(c_991010_80)
    assert siblings == [c_991020]


def test_snapshot_get_children_suffixes_indents(collection_suffixes_indents):
    snapshot = collection_suffixes_indents.current_snapshot

    c_991010_10 = snapshot.get_commodity("9910.10", "10")
    c_991010_80 = snapshot.get_commodity("9910.10")
    c_991020 = snapshot.get_commodity("9910.20")

    children = snapshot.get_children(c_991010_10)
    assert children == [c_991010_80, c_991020]


def test_snapshot_commodity_is_declarable(collection_basic):
    snapshot = collection_basic.current_snapshot

    c_9999 = snapshot.get_commodity("9999")
    c_999910 = snapshot.get_commodity("9999.10")

    assert snapshot.is_declarable(c_9999) is False
    assert snapshot.is_declarable(c_999910) is True


def test_change_valid_create(collection_basic, commodities):
    commodity = commodities["9999.20.00.10_80_3"]

    with not_raises(ValueError):
        CommodityChange(
            collection=collection_basic,
            candidate=commodity,
            update_type=UpdateType.CREATE,
        )


def test_change_invalid_create_no_comodity(collection_basic):
    with pytest.raises(ValueError):
        CommodityChange(
            collection=collection_basic,
            update_type=UpdateType.CREATE,
        )


def test_change_invalid_create_clash(collection_basic):
    current = collection_basic.get_commodity("9999.20")
    commodity = copy_commodity(current, indent=current.indent + 1)

    with pytest.raises(ValueError):
        CommodityChange(
            collection=collection_basic,
            candidate=commodity,
            update_type=UpdateType.CREATE,
        )


def test_change_valid_update(collection_basic):
    current = collection_basic.get_commodity("9999.20")
    commodity = copy_commodity(current, suffix="20")

    with not_raises(ValueError):
        CommodityChange(
            collection=collection_basic,
            current=current,
            candidate=commodity,
            update_type=UpdateType.UPDATE,
        )


def test_change_invalid_update_no_current(collection_basic):
    commodity = copy_commodity(
        collection_basic.get_commodity("9999.20"),
        suffix="20",
    )

    with pytest.raises(ValueError):
        CommodityChange(
            collection=collection_basic,
            candidate=commodity,
            update_type=UpdateType.UPDATE,
        )


def test_change_invalid_update_no_change(collection_basic):
    current = collection_basic.get_commodity("9999.20")
    commodity = copy_commodity(current)

    with pytest.raises(ValueError):
        CommodityChange(
            collection=collection_basic,
            current=current,
            candidate=commodity,
            update_type=UpdateType.UPDATE,
        )


def test_change_valid_delete(collection_basic):
    current = collection_basic.get_commodity("9999.20")

    with not_raises(ValueError):
        CommodityChange(
            collection=collection_basic,
            current=current,
            update_type=UpdateType.DELETE,
        )


def test_change_invalid_delete_no_current(collection_basic):
    with pytest.raises(ValueError):
        CommodityChange(
            collection=collection_basic,
            update_type=UpdateType.UPDATE,
        )


def test_change_effects_create(collection_basic, commodities):
    group = collection_basic.clone()

    commodity = commodities["9999.20.00.10_80_3"]

    updates = [
        CommodityChange(
            collection=group,
            candidate=commodity,
            update_type=UpdateType.CREATE,
        ),
    ]

    group.update(updates)
    assert commodity in group.commodities


def test_change_effects_update(collection_basic):
    group = collection_basic.clone()

    code = "9999.20"
    suffix = "20"
    current = group.get_commodity(code)
    candidate = copy_commodity(current, suffix=suffix)

    updates = [
        CommodityChange(
            collection=group,
            current=current,
            candidate=candidate,
            update_type=UpdateType.UPDATE,
        ),
    ]

    group.update(updates)
    assert group.get_commodity(code) is None
    assert group.get_commodity(code, suffix) is not None


def test_change_effects_delete(collection_basic, commodities):
    group = collection_basic.clone()

    commodity = commodities["9999.20_80_2"]

    updates = [
        CommodityChange(
            collection=group,
            current=commodity,
            update_type=UpdateType.DELETE,
        ),
    ]

    group.update(updates)
    assert commodity not in group.commodities
