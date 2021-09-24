import re
from copy import copy
from datetime import date
from datetime import timedelta

import pytest

from commodities.models.constants import SUFFIX_DECLARABLE
from commodities.models.dc import CommodityChange
from commodities.models.dc import CommodityTreeBase
from common.util import TaricDateRange
from common.validators import UpdateType

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


def test_commodity_code(commodities):
    for commodity in commodities.values():
        assert str(commodity.code) == commodity.get_item_id()


def test_commodity_dot_code(commodities):
    for commodity in commodities.values():
        code = commodity.code
        dot_code = commodity.code.dot_code

        assert len(dot_code) == 13
        assert dot_code.count(".") == 3
        assert dot_code.replace(".", "") == str(code)


def test_commodity_trimmed_code(commodities):
    for commodity in commodities.values():
        trimmed_code = commodity.code.trimmed_code
        tail = str(commodity.code).replace(trimmed_code, "")

        assert len(trimmed_code) >= 4
        assert tail.count("0") == len(tail)
        assert len(tail) % 2 == 0


def test_commodity_trimmed_dot_code(commodities):
    for commodity in commodities.values():
        trimmed_dot_code = commodity.code.trimmed_dot_code
        dot_code = commodity.code.dot_code
        tail = dot_code.replace(trimmed_dot_code, "")

        assert len(trimmed_dot_code) >= 4
        assert tail.count("0") + tail.count(".") == len(tail)
        assert len(tail) % 3 == 0


def test_commodity_code_levels(commodities):
    for commodity in commodities.values():
        assert len(commodity.code.chapter) == 2
        assert len(commodity.code.heading) == 4
        assert len(commodity.code.subheading) == 6
        assert len(commodity.code.cn_subheading) == 8
        assert len(str(commodity.code)) == 10


def test_commodity_is_chapter(commodities):
    for commodity in commodities.values():
        code = str(commodity.code)
        n = len(code.replace("00", ""))
        assert commodity.code.is_chapter == (n == 2)


def test_commodity_is_heading(commodities):
    for commodity in commodities.values():
        code = commodity.code.trimmed_dot_code

        m = len(code[2:4].replace("00", ""))
        n = len(code[4:].replace(".00", ""))

        is_heading = m != 0 and n == 0
        assert commodity.code.is_heading == is_heading


def test_commodity_is_subheading(commodities):
    for commodity in commodities.values():
        code = commodity.code.trimmed_dot_code

        m = len(code[4:].replace(".00", "").replace(".", ""))
        n = len(code[7:].replace(".00", "").replace(".", ""))

        is_subheading = m != 0 and n == 0
        assert commodity.code.is_subheading == is_subheading


def test_commodity_is_cn_subheading(commodities):
    for commodity in commodities.values():
        code = commodity.code.trimmed_dot_code

        m = len(code[7:].replace(".00", "").replace(".", ""))
        n = len(code[10:].replace(".00", "").replace(".", ""))

        is_cn_subheading = m != 0 and n == 0
        assert commodity.code.is_cn_subheading == is_cn_subheading


def test_commodity_is_taric_subheading(commodities):
    for commodity in commodities.values():
        code = commodity.code.trimmed_dot_code

        m = len(code[7:].replace(".00", "").replace(".", ""))
        n = len(code[10:].replace(".00", "").replace(".", ""))

        is_taric_subheading = m != 0 and n != 0
        assert commodity.code.is_taric_subheading == is_taric_subheading


def test_commodity_suffix(commodities):
    used_conftest_suffixes = ("10", "80")

    for commodity in commodities.values():
        assert len(commodity.get_suffix()) == 2
        assert commodity.get_suffix() == commodity.obj.suffix
        assert commodity.get_suffix() in used_conftest_suffixes


def test_commodity_dates(commodities):
    for commodity in commodities.values():
        date_range = TaricDateRange(
            commodity.start_date,
            commodity.end_date,
        )

        assert date_range == commodity.obj.valid_between


def test_commodity_get_indent(commodities):
    for commodity in commodities.values():
        a = commodity.indent is not None
        b = commodity.get_indent() == commodity.indent

        assert a == b


def test_commodity_identifier(commodities):
    re_identifier = re.compile(r"([0-9.]{13})-([1-8]{1}0)-([0-9]{1,2})/([0-9]{1})")

    for commodity in commodities.values():
        try:
            match = next(re_identifier.finditer(commodity.identifier))
        except StopIteration:
            pytest.fail("Expected at least one commodity identifier")

        groups = match.groups()

        assert len(groups) == 4
        code, suffix, indent, version = groups

        assert code == commodity.code.dot_code
        assert suffix == commodity.get_suffix()
        assert indent == str(commodity.get_indent())
        assert version == str(commodity.version)


def test_commodity_tree_base_get_commodity(commodities):
    base = CommodityTreeBase(commodities=commodities.values())
    suffixes = (None, "10", "80")
    versions = (None, 0, 1, 2)

    for commodity in commodities.values():
        kwargs = dict(code=str(commodity.code))

        for suffix in suffixes:
            if suffix is not None:
                kwargs.update(dict(suffix=suffix))

            for version in versions:
                kwargs.update(dict(version=version))

                result = base.get_commodity(**kwargs)
                suffix = suffix or SUFFIX_DECLARABLE
                version = version or commodity.current_version

                a = result == commodity
                b = suffix == commodity.get_suffix() and version == commodity.version

                assert a == b


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
    ids=[
        "snapshot-today",
        "snapshot-yesterday",
        "snapshot-15-days-ahead",
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


def test_collection_get_transaction_clock_snapshot(collection_full):
    transaction_ids = sorted(
        [commodity.obj.transaction.id for commodity in collection_full.commodities],
    )
    commodities = collection_full.commodities[::-1]

    for i, transaction_id in enumerate(transaction_ids):
        snapshot = collection_full.get_transaction_clock_snapshot(
            transaction_id=transaction_id,
        )

        assert snapshot.commodities[::-1] == commodities[: i + 1]


def test_collection_current_snapshot(collection_full):
    snapshot = collection_full.current_snapshot

    transaction_id = collection_full.max_transaction_id
    snapshot_date = date.today()
    tx_snapshot = collection_full.get_transaction_clock_snapshot(transaction_id)
    cal_snapshot = collection_full.get_calendar_clock_snapshot(snapshot_date)

    tx_commodities = set(x.identifier for x in tx_snapshot.commodities)
    cal_commodities = set(x.identifier for x in cal_snapshot.commodities)
    tx_cal_commodities = tx_commodities.intersection(cal_commodities)

    commodities = set(x.identifier for x in snapshot.commodities)

    assert snapshot.moments == (snapshot_date, transaction_id)
    assert sorted(commodities) == sorted(tx_cal_commodities)


def test_collection_clone(collection_full):
    n = len(collection_full.commodities)
    collection_cloned = copy(collection_full)
    collection_cloned.commodities.pop()

    assert len(collection_full.commodities) == n


def test_collection_update_create(collection_basic, commodities):
    group = copy(collection_basic)

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


def test_collection_update_update(collection_basic, transaction_pool):
    group = copy(collection_basic)

    code = "9999.20"
    suffix = "20"
    current = group.get_commodity(code)
    candidate = copy_commodity(current, transaction_pool, suffix=suffix)

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


def test_collection_update_delete(collection_basic, commodities):
    group = copy(collection_basic)

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


def test_snapshot_get_parent_headings_zero_indent(collection_headings):
    snapshot = collection_headings.current_snapshot

    c_99 = snapshot.get_commodity("99")
    c_9905_10 = snapshot.get_commodity("9905", suffix="10")
    c_9905_80 = snapshot.get_commodity("9905")
    c_9910_10 = snapshot.get_commodity("9910", suffix="10")
    c_9910_80 = snapshot.get_commodity("9910")

    assert snapshot.get_parent(c_9905_10) == c_99
    assert snapshot.get_parent(c_9910_10) == c_99
    assert snapshot.get_parent(c_9905_80) == c_9905_10
    assert snapshot.get_parent(c_9910_80) == c_9910_10


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


def test_snapshot_get_ancestors(collection_full):
    snapshot = collection_full.current_snapshot

    c_99 = snapshot.get_commodity("99")
    c_9910_10 = snapshot.get_commodity("9910", suffix="10")
    c_9910_80 = snapshot.get_commodity("9910")
    c_9999 = snapshot.get_commodity("9999")
    c_9999200000 = snapshot.get_commodity("9999.20.00.00")
    c_9999200010 = snapshot.get_commodity("9999.20.00.10")

    assert snapshot.get_ancestors(c_99) == []
    assert snapshot.get_ancestors(c_9999) == [c_99, c_9910_10, c_9910_80]
    assert snapshot.get_ancestors(c_9999200010) == [
        c_99,
        c_9910_10,
        c_9910_80,
        c_9999,
        c_9999200000,
    ]


def test_snapshot_get_descendants(collection_full):
    snapshot = collection_full.current_snapshot
    commodities = snapshot.commodities

    for commodity in commodities:
        ancestors = snapshot.get_ancestors(commodity)
        non_ancestors = [
            commodity_ for commodity_ in commodities if commodity_ not in ancestors
        ]

        for ancestor in ancestors:
            assert commodity in snapshot.get_descendants(ancestor)
        for commodity_ in non_ancestors:
            assert commodity not in snapshot.get_descendants(commodity_)


def test_snapshot_is_declarable(collection_basic):
    snapshot = collection_basic.current_snapshot

    c_9999 = snapshot.get_commodity("9999")
    c_999910 = snapshot.get_commodity("9999.10")

    assert not snapshot.is_declarable(c_9999)
    assert snapshot.is_declarable(c_999910)


def test_snapshot_date(collection_basic):
    snapshot_date = date.today()
    transaction_id = collection_basic.max_transaction_id

    snapshot = collection_basic.get_calendar_clock_snapshot(snapshot_date)
    assert snapshot.snapshot_date == snapshot_date
    assert snapshot.moments == (snapshot_date, transaction_id)

    transaction_id = collection_basic.max_transaction_id
    snapshot = collection_basic.get_transaction_clock_snapshot(transaction_id)
    assert snapshot.snapshot_date is None


def test_snapshot_transaction_id(collection_basic):
    snapshot_date = date.today()
    transaction_id = collection_basic.max_transaction_id

    snapshot = collection_basic.get_calendar_clock_snapshot(snapshot_date)
    assert snapshot.snapshot_transaction_id is None

    snapshot = collection_basic.get_transaction_clock_snapshot(transaction_id)
    assert snapshot.snapshot_transaction_id == transaction_id
    assert snapshot.moments == (snapshot_date, transaction_id)


def test_change_valid_create(collection_basic, commodities):
    commodity = commodities["9999.20.00.10_80_3"]

    assert CommodityChange(
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


def test_change_invalid_create_clash(collection_basic, transaction_pool):
    current = collection_basic.get_commodity("9999.20")
    commodity = copy_commodity(current, transaction_pool, indent=current.indent + 1)

    with pytest.raises(ValueError):
        CommodityChange(
            collection=collection_basic,
            candidate=commodity,
            update_type=UpdateType.CREATE,
        )


def test_change_valid_update(collection_basic, transaction_pool):
    current = collection_basic.get_commodity("9999.20")
    commodity = copy_commodity(current, transaction_pool, suffix="20")

    assert CommodityChange(
        collection=collection_basic,
        current=current,
        candidate=commodity,
        update_type=UpdateType.UPDATE,
    )


def test_change_invalid_update_no_current(collection_basic, transaction_pool):
    current = collection_basic.get_commodity("9999.20")
    commodity = copy_commodity(current, transaction_pool, suffix="20")

    with pytest.raises(ValueError):
        CommodityChange(
            collection=collection_basic,
            candidate=commodity,
            update_type=UpdateType.UPDATE,
        )


def test_change_invalid_update_no_change(collection_basic, transaction_pool):
    current = collection_basic.get_commodity("9999.20")
    commodity = copy_commodity(current, transaction_pool)

    with pytest.raises(ValueError):
        CommodityChange(
            collection=collection_basic,
            current=current,
            candidate=commodity,
            update_type=UpdateType.UPDATE,
        )


def test_change_valid_delete(collection_basic):
    current = collection_basic.get_commodity("9999.20")

    assert CommodityChange(
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


def test_snapshot_diff_create(collection_basic, commodities):
    collection = copy(collection_basic)

    parent = collection.get_commodity("9999.20")
    candidate = commodities["9999.20.00.10_80_3"]

    updates = [
        CommodityChange(
            collection=collection,
            candidate=candidate,
            update_type=UpdateType.CREATE,
        ),
    ]

    before = collection.current_snapshot
    collection.update(updates)
    after = collection.current_snapshot

    snapshot_diff = after.compare_children(parent, before)
    assert snapshot_diff.diff == [candidate]


def test_snapshot_diff_update(collection_basic, transaction_pool):
    collection = copy(collection_basic)

    parent = collection.get_commodity("9999")
    sibling = collection.get_commodity("9999.10")

    current = collection.get_commodity("9999.20")
    candidate = copy_commodity(
        current,
        transaction_pool,
        indent=current.get_indent() + 1,
    )

    updates = [
        CommodityChange(
            collection=collection,
            current=current,
            candidate=candidate,
            update_type=UpdateType.UPDATE,
        ),
    ]

    before = collection.current_snapshot
    collection.update(updates)
    after = collection.current_snapshot

    snapshot_diff = after.compare_children(parent, before)
    assert snapshot_diff.diff == [current]

    snapshot_diff = after.compare_children(sibling, before)
    assert snapshot_diff.diff == [candidate]

    snapshot_diff = after.compare_siblings(sibling, before)
    assert snapshot_diff.diff == [current]

    snapshot_diff = before.compare_parents(current, after)
    assert snapshot_diff.diff == [parent]

    snapshot_diff = after.compare_parents(candidate, before)
    assert snapshot_diff.diff == [sibling]


def test_snapshot_diff_delete(collection_basic):
    collection = copy(collection_basic)

    parent = collection.get_commodity("9999")
    current = collection.get_commodity("9999.20")

    updates = [
        CommodityChange(
            collection=collection,
            current=current,
            update_type=UpdateType.DELETE,
        ),
    ]

    before = collection.current_snapshot
    collection.update(updates)
    after = collection.current_snapshot

    snapshot_diff = after.compare_children(parent, before)
    assert snapshot_diff.diff == [current]
    snapshot_diff = before.compare_parents(current, after)
    assert snapshot_diff.diff == [parent]
