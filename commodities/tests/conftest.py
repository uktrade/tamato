from typing import Dict
from typing import Iterator
from typing import List
from typing import Tuple

import pytest

from commodities.models.dc import Commodity
from commodities.models.dc import CommodityChange
from commodities.models.dc import CommodityCollection
from commodities.models.orm import FootnoteAssociationGoodsNomenclature
from common.models.transactions import Transaction
from common.tests import factories
from common.util import TaricDateRange
from common.validators import UpdateType
from measures.models import Measure
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

TScenario = Tuple[CommodityCollection, List[CommodityChange]]


def copy_commodity(
    commodity: Commodity, transaction_pool: Iterator[Transaction], **kwargs
) -> Commodity:
    meta = commodity.obj._meta

    attrs = {
        field.name: getattr(commodity.obj, field.name)
        for field in meta.fields
        if field.name not in commodity.obj.system_set_field_names
        if field.name != "sid"
    }

    attrs.update(kwargs)

    transaction = next(transaction_pool)

    obj = factories.GoodsNomenclatureFactory.create(transaction=transaction, **attrs)
    indent = kwargs.get("indent", commodity.indent)
    return Commodity(obj=obj, indent=indent)


def create_commodity(
    transaction_pool: Iterator[Transaction],
    code: str,
    suffix: str,
    indent: int,
    validity: TaricDateRange,
) -> Commodity:
    item_id = code.replace(".", "")

    transaction = next(transaction_pool)

    obj = factories.GoodsNomenclatureFactory.create(
        item_id=item_id,
        suffix=suffix,
        valid_between=validity,
        transaction=transaction,
    )

    return Commodity(obj=obj, indent=indent)


def create_collection(
    commodities: List[Commodity],
    keys: List[str] = None,
) -> CommodityCollection:
    keys = keys or commodities.keys()
    members = [commodities[key] for key in keys]

    return CommodityCollection(commodities=members)


def create_dependent_measure(
    commodity: Commodity, transaction_pool: Iterator[Transaction], **kwargs
) -> Measure:
    factory = factories.MeasureFactory

    transaction = next(transaction_pool)
    workbasket = transaction.workbasket

    measure = factory.create(transaction=transaction, **kwargs)

    return measure.new_version(
        workbasket=workbasket,
        transaction=transaction,
        goods_nomenclature=commodity.obj,
    )


def create_footnote_association(
    commodity: Commodity, transaction_pool: Iterator[Transaction], **kwargs
) -> FootnoteAssociationGoodsNomenclature:
    factory = factories.FootnoteAssociationGoodsNomenclatureFactory

    transaction = next(transaction_pool)
    transaction.workbasket

    return factory.create(
        transaction=transaction, goods_nomenclature=commodity.obj, **kwargs
    )


@pytest.fixture
def workbasket() -> WorkBasket:
    return factories.WorkBasketFactory(
        status=WorkflowStatus.PUBLISHED,
    )


@pytest.fixture
def transaction_pool(workbasket) -> Iterator[Transaction]:
    factory = factories.TransactionFactory

    transactions = [factory.create(workbasket=workbasket) for _ in range(50)][::-1]

    return iter(transactions)


@pytest.fixture
def normal_good(date_ranges, transaction_pool):
    return factories.GoodsNomenclatureFactory.create(
        valid_between=date_ranges.normal,
        transaction=next(transaction_pool),
    )


@pytest.fixture
def commodities(date_ranges, transaction_pool) -> Dict[str, Commodity]:
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

    commodities = [create_commodity(transaction_pool, *args) for args in params]
    keys = [f"{c.trimmed_dot_code}_{c.suffix}_{c.indent}" for c in commodities]
    return dict(zip(keys, commodities))


@pytest.fixture
def commodities_spanned(date_ranges, transaction_pool):
    params = (
        ("9999.00.00.00", "80", 1, date_ranges.no_end),
        ("9999.10.00.00", "80", 2, date_ranges.normal),
        ("9999.10.10.00", "80", 3, date_ranges.overlap_normal),
        ("9999.10.20.00", "80", 3, date_ranges.overlap_normal_earlier),
        ("9999.20.00.00", "80", 2, date_ranges.adjacent),
        ("9999.20.10.00", "80", 3, date_ranges.adjacent_earlier),
        ("9999.20.20.00", "80", 3, date_ranges.future),
    )

    commodities = [create_commodity(transaction_pool, *args) for args in params]
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
def scenario_2(collection_basic, transaction_pool) -> TScenario:
    collection = collection_basic.clone()

    commodity = collection.get_commodity("9999.20")

    create_dependent_measure(commodity, transaction_pool)
    create_footnote_association(commodity, transaction_pool)

    changes = [
        CommodityChange(
            collection=collection,
            current=commodity,
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
def scenario_4(collection_basic, date_ranges, transaction_pool) -> TScenario:
    collection = collection_basic.clone()

    current = collection.get_commodity("9999.20")

    attrs = dict(valid_between=date_ranges.overlap_normal_same_year)
    candidate = copy_commodity(current, transaction_pool, **attrs)

    attrs = dict(valid_between=date_ranges.normal)
    create_dependent_measure(candidate, transaction_pool, **attrs)
    create_footnote_association(candidate, transaction_pool, **attrs)

    attrs = dict(valid_between=date_ranges.overlap_normal_earlier)
    create_dependent_measure(candidate, transaction_pool, **attrs)
    create_footnote_association(candidate, transaction_pool, **attrs)

    print(1)

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
def scenario_5(collection_basic, commodities, transaction_pool) -> TScenario:
    collection = collection_basic.clone()

    current = collection.get_commodity("9999.20")
    candidate = copy_commodity(current, transaction_pool, suffix="20")
    create_dependent_measure(candidate, transaction_pool)

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
def scenario_6(collection_basic, transaction_pool) -> TScenario:
    collection = collection_basic.clone()

    current = collection.get_commodity("9999.20")
    candidate = copy_commodity(current, transaction_pool, indent=current.indent + 1)

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
def scenario_7(commodities, transaction_pool) -> TScenario:
    keys = [
        "9999_80_1",
        "9999.10_80_2",
        "9999.20_80_2",
        "9999.20.00.10_80_3",
    ]
    collection = create_collection(commodities, keys)

    current = collection.get_commodity("9999.20")
    candidate = copy_commodity(current, transaction_pool, indent=current.indent + 1)

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
def scenario_8(scenario_7, transaction_pool) -> TScenario:
    collection, changes = scenario_7
    collection.update(changes)

    current = collection.get_commodity("9999.20")
    candidate = copy_commodity(current, transaction_pool, indent=current.indent - 1)

    changes = [
        CommodityChange(
            collection=collection,
            current=current,
            candidate=candidate,
            update_type=UpdateType.UPDATE,
        ),
    ]

    return (collection, changes)
