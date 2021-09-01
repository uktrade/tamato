from datetime import timedelta
from typing import Dict
from typing import List
from typing import Tuple

import pytest

from commodities.models.dc import Commodity
from commodities.models.dc import CommodityChange
from commodities.models.dc import CommodityCollection
from common.tests import factories
from common.util import TaricDateRange
from common.validators import UpdateType

TScenario = Tuple[CommodityCollection, List[CommodityChange]]


def copy_commodity(commodity: Commodity, **kwargs) -> Commodity:
    meta = commodity.obj._meta

    attrs = {
        field.name: getattr(commodity.obj, field.name)
        for field in meta.fields
        if field.name not in commodity.obj.system_set_field_names
    }
    attrs.update(kwargs)

    obj = factories.GoodsNomenclatureFactory.create(**attrs)
    indent = kwargs.get("indent", commodity.indent)
    return Commodity(obj=obj, indent=indent)


def create_commodity(
    code: str,
    suffix: str,
    indent: int,
    validity: TaricDateRange,
) -> Commodity:
    item_id = code.replace(".", "")

    obj = factories.GoodsNomenclatureFactory.create(
        item_id=item_id,
        suffix=suffix,
        valid_between=validity,
    )

    return Commodity(obj=obj, indent=indent)


def create_collection(
    commodities: List[Commodity],
    keys: List[str] = None,
) -> CommodityCollection:
    keys = keys or commodities.keys()
    members = [commodities[key] for key in keys]
    return CommodityCollection(commodities=members)


@pytest.fixture
def normal_good(date_ranges):
    return factories.GoodsNomenclatureFactory.create(valid_between=date_ranges.normal)


@pytest.fixture
def commodities(date_ranges) -> Dict[str, Commodity]:
    params = (
        ("9900.00.00.00", "80", 0, date_ranges.normal),
        ("9910.00.00.00", "80", 0, date_ranges.normal),
        ("9910.10.00.00", "10", 1, date_ranges.normal),
        ("9910.10.00.00", "80", 2, date_ranges.normal),
        ("9910.20.00.00", "80", 2, date_ranges.normal),
        ("9999.00.00.00", "80", 1, date_ranges.normal),
        ("9999.10.00.00", "80", 2, date_ranges.normal),
        ("9999.20.00.00", "80", 2, date_ranges.normal),
        ("9999.20.00.10", "80", 3, date_ranges.normal),
    )

    commodities = [create_commodity(*args) for args in params]
    keys = [f"{c.trimmed_dot_code}_{c.suffix}_{c.indent}" for c in commodities]
    return dict(zip(keys, commodities))


@pytest.fixture
def commodities_spanned(date_ranges):
    params = (
        ("9999.00.00.00", "80", 1, date_ranges.no_end),
        ("9999.10.00.00", "80", 2, date_ranges.normal),
        ("9999.10.10.00", "80", 3, date_ranges.overlap_normal),
        ("9999.10.20.00", "80", 3, date_ranges.overlap_normal_earlier),
        ("9999.20.00.00", "80", 2, date_ranges.adjacent),
        ("9999.20.10.00", "80", 3, date_ranges.adjacent_earlier),
        ("9999.20.20.00", "80", 3, date_ranges.future),
    )

    commodities = [create_commodity(*args) for args in params]
    keys = [f"{c.trimmed_dot_code}_{c.suffix}_{c.indent}" for c in commodities]
    return dict(zip(keys, commodities))


@pytest.fixture
def collection_basic(commodities) -> CommodityCollection:
    keys = ["9999_80_1", "9999.10_80_2", "9999.20_80_2"]
    return create_collection(commodities, keys)


@pytest.fixture
def collection_heading(commodities) -> CommodityCollection:
    keys = ["9900_80_0", "9910_80_0"]
    return create_collection(commodities, keys)


@pytest.fixture
def collection_suffixes_indents(commodities) -> CommodityCollection:
    keys = ["9910.10_10_1", "9910.10_80_2", "9910.20_80_2"]
    return create_collection(commodities, keys)


@pytest.fixture
def collection_full(commodities) -> CommodityCollection:
    return create_collection(commodities)


@pytest.fixture
def collection_spanned(commodities_spanned) -> CommodityCollection:
    return create_collection(commodities_spanned)


@pytest.fixture
def scenario_1(commodities) -> TScenario:
    keys = ["9999_80_1", "9999.10_80_2"]
    collection = create_collection(commodities, keys)

    changes = [
        CommodityChange(
            collection=collection,
            candidate=commodities["9999.20_80_2"],
            update_type=UpdateType.CREATE,
        ),
    ]

    return (collection, changes)


@pytest.fixture
def scenario_2(collection_basic) -> TScenario:
    collection = collection_basic.clone()

    changes = [
        CommodityChange(
            collection=collection,
            current=collection.get_commodity("9999.20"),
            update_type=UpdateType.DELETE,
        ),
    ]

    return (collection, changes)


@pytest.fixture
def scenario_3(commodities) -> TScenario:
    keys = [
        "9999_80_1",
        "9999.10_80_2",
        "9999.20_80_2",
        "9999.20.00.10_80_3",
    ]
    collection = create_collection(commodities, keys)

    changes = [
        CommodityChange(
            collection=collection,
            current=collection.get_commodity("9999.20"),
            update_type=UpdateType.DELETE,
        ),
    ]

    return (collection, changes)


@pytest.fixture
def scenario_4(collection_basic) -> TScenario:
    collection = collection_basic.clone()

    commodity = collection.get_commodity("9999.20")

    valid_between = TaricDateRange(
        commodity.obj.valid_between.lower,
        commodity.obj.valid_between.lower + timedelta(days=10),
    )
    candidate = copy_commodity(commodity, valid_between=valid_between)

    changes = [
        CommodityChange(
            collection=collection,
            current=commodity,
            candidate=candidate,
            update_type=UpdateType.UPDATE,
        ),
    ]

    return (collection, changes)


@pytest.fixture
def scenario_5(collection_basic, commodities) -> TScenario:
    collection = collection_basic.clone()

    current = collection.get_commodity("9999.20")
    candidate = copy_commodity(current, suffix="20")

    changes = [
        CommodityChange(
            collection=collection,
            candidate=commodities["9999.20.00.10_80_3"],
            update_type=UpdateType.CREATE,
        ),
        CommodityChange(
            collection=collection,
            current=current,
            candidate=candidate,
            update_type=UpdateType.UPDATE,
        ),
    ]

    return (collection, changes)


@pytest.fixture
def scenario_6(collection_basic) -> TScenario:
    collection = collection_basic.clone()

    current = collection.get_commodity("9999.20")
    candidate = copy_commodity(current, indent=current.indent + 1)

    changes = [
        CommodityChange(
            collection=collection,
            current=current,
            candidate=candidate,
            update_type=UpdateType.UPDATE,
        ),
    ]

    return (collection, changes)


@pytest.fixture
def scenario_7(commodities) -> TScenario:
    keys = [
        "9999_80_1",
        "9999.10_80_2",
        "9999.20_80_2",
        "9999.20.00.10_80_3",
    ]
    collection = create_collection(commodities, keys)

    current = collection.get_commodity("9999.20")
    candidate = copy_commodity(current, indent=current.indent + 1)

    changes = [
        CommodityChange(
            collection=collection,
            current=current,
            candidate=candidate,
            update_type=UpdateType.UPDATE,
        ),
    ]

    return (collection, changes)


@pytest.fixture
def scenario_8(scenario_7) -> TScenario:
    collection, changes = scenario_7
    collection.update(changes)

    current = collection.get_commodity("9999.20")
    candidate = copy_commodity(current, indent=current.indent - 1)

    changes = [
        CommodityChange(
            collection=collection,
            current=current,
            candidate=candidate,
            update_type=UpdateType.UPDATE,
        ),
    ]

    return (collection, changes)
