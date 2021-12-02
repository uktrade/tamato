"""
Provides fixtures for commodity application tests.

Scenario fixtures in particular reflect the scenarios in ADR13.
- Each fixture provides the SETUP for the scenario in terms of
  initial tree state and pending commodity changes
- The changes are applied by the respective test using the fixture,
  which results in the END-STATE of the tree, at which point
  the test the new hierarchy as well as any side effects.

An important note on transaction sequencing in the below fixtures:
- As we change the commodity tree, we need to detect side effects
  on related measures, footnote associations, etc.
- In order to avoid creating duplicate logic in our app,
  we leverage existing business rules for detecting any side effects
- This involves a mix of goods-centric business rules (NIG-s)
  and measure-centric business rules (ME-s)
- Sometimes, NIG-s will look for measures approved as of a good's transaction
  and ME-s will look for goods approved as of a mesure's transaction
- In order to properly configure the fixtures,
  we use a small transaction pool with transactions in descending order
  where needed, retaining the ability to add delayed_transactions as well
"""

from __future__ import annotations

from copy import copy
from typing import Iterator
from typing import List
from typing import Optional
from typing import Sequence
from typing import Tuple
from typing import Union

import pytest
import responses

from commodities.models.dc import Commodity
from commodities.models.dc import CommodityChange
from commodities.models.dc import CommodityCollection
from commodities.models.orm import FootnoteAssociationGoodsNomenclature
from common.models.trackedmodel import TrackedModel
from common.models.transactions import Transaction
from common.tests import factories
from common.util import TaricDateRange
from common.validators import UpdateType
from importer.reports import URL_DEF
from measures.models import Measure
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

TScenario = Tuple[CommodityCollection, List[CommodityChange]]


@pytest.fixture
def mocked_responses():
    """Provides a mocked responses fixture for use with commodity importer
    tests."""
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, url=URL_DEF)
        yield rsps


def copy_commodity(
    commodity: Commodity, transaction_pool: Iterator[Transaction], **kwargs
) -> Commodity:
    """Returns a copy of a commodity wrapper with modified attributes."""
    meta = commodity.obj._meta

    attrs = {
        field.name: getattr(commodity.obj, field.name)
        for field in meta.fields
        if field.name not in commodity.obj.system_set_field_names
        if field.name != "sid"
    }

    attrs["indent__indent"] = kwargs.pop("indent", commodity.indent)
    attrs.update(kwargs)

    transaction = next(transaction_pool)

    obj = factories.GoodsNomenclatureFactory.create(transaction=transaction, **attrs)
    return Commodity(obj=obj, indent_obj=obj.indents.get())


def create_commodity(
    transaction_pool: Iterator[Transaction],
    code: str,
    suffix: str,
    indent: int,
    validity: TaricDateRange,
) -> Commodity:
    """Returns a new commodity wrapper with the provided attributes."""
    item_id = code.replace(".", "")

    transaction = next(transaction_pool)

    obj = factories.GoodsNomenclatureFactory.create(
        item_id=item_id,
        suffix=suffix,
        valid_between=validity,
        transaction=transaction,
        indent__indent=indent,
    )

    return Commodity(obj=obj, indent_obj=obj.indents.get())


def create_collection(
    commodities: Union[list[Commodity], dict[str, Commodity]],
    keys: Optional[Sequence[str]] = None,
) -> CommodityCollection:
    """Returns a new CommodityCollection with the selected commodities."""
    keys = keys or commodities.keys()
    members = [commodities[key] for key in keys]

    return CommodityCollection(commodities=members)


def create_record(
    transaction_pool: Iterator[Transaction], factory, **kwargs
) -> TrackedModel:
    """
    Returns a new TrackedModel instance.

    See the module-level docs for details on the use of the transaction_pool.
    """
    if "transaction" not in kwargs:
        kwargs["transaction"] = next(transaction_pool)
    return factory.create(**kwargs)


def create_dependent_measure(
    commodity: Commodity, transaction_pool: Iterator[Transaction], **kwargs
) -> Measure:
    """Returns a new measure linked to a given good."""
    factory = factories.MeasureFactory
    measure = create_record(transaction_pool, factory, **kwargs)

    transaction = measure.transaction
    workbasket = transaction.workbasket

    return measure.new_version(
        workbasket=workbasket,
        transaction=transaction,
        goods_nomenclature=commodity.obj,
    )


def create_footnote_association(
    commodity: Commodity, transaction_pool: Iterator[Transaction], **kwargs
) -> FootnoteAssociationGoodsNomenclature:
    """Returns a new footnote association linked to a given good."""
    factory = factories.FootnoteAssociationGoodsNomenclatureFactory
    association = create_record(transaction_pool, factory, **kwargs)

    transaction = association.transaction
    workbasket = transaction.workbasket

    return association.new_version(
        workbasket=workbasket,
        transaction=transaction,
        goods_nomenclature=commodity.obj,
    )


@pytest.fixture
def workbasket() -> WorkBasket:
    """Provides a workbasket for use across fixtures."""
    return factories.WorkBasketFactory(
        status=WorkflowStatus.PUBLISHED,
    )


@pytest.fixture
def transaction_pool(workbasket) -> Iterator[Transaction]:
    """
    Returns an iterator with transactions in descending order of id.

    See the module-level docs for details on the use of the transaction_pool.
    """
    factory = factories.TransactionFactory

    transactions = reversed(factory.create_batch(50, workbasket=workbasket))

    return iter(transactions)


@pytest.fixture
def normal_good(date_ranges, transaction_pool):
    return factories.GoodsNomenclatureFactory.create(
        valid_between=date_ranges.normal,
        transaction=next(transaction_pool),
    )


@pytest.fixture
def commodities(date_ranges, transaction_pool) -> dict[str, Commodity]:
    params = (
        ("9900.00.00.00", "80", 0, date_ranges.normal),
        ("9905.00.00.00", "10", 0, date_ranges.normal),
        ("9905.00.00.00", "80", 0, date_ranges.normal),
        ("9910.00.00.00", "10", 0, date_ranges.normal),
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

    return {f"{c.code.trimmed_dot_code}_{c.suffix}_{c.indent}": c for c in commodities}


@pytest.fixture
def commodities_spanned(date_ranges, transaction_pool):
    """
    Returns a list of commodities with various validity periods.

    This is useful for tests of date range related side effects arising from
    commodity code changes.
    """
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
    return {f"{c.code.trimmed_dot_code}_{c.suffix}_{c.indent}": c for c in commodities}


@pytest.fixture
def collection_basic(commodities) -> CommodityCollection:
    """Returns a simple collection of commodities side effects testing."""
    keys = ["9999_80_1", "9999.10_80_2", "9999.20_80_2"]
    return create_collection(commodities, keys)


@pytest.fixture
def collection_headings(commodities) -> CommodityCollection:
    """Returns a special collection of headings to test header and chapter
    parenting rules."""
    keys = ["9900_80_0", "9905_10_0", "9905_80_0", "9910_10_0", "9910_80_0"]
    return create_collection(commodities, keys)


@pytest.fixture
def collection_suffixes_indents(commodities) -> CommodityCollection:
    """Returns a collection of indented commodities to test tree hierarchies."""
    keys = ["9910.10_10_1", "9910.10_80_2", "9910.20_80_2"]
    return create_collection(commodities, keys)


@pytest.fixture
def collection_full(commodities) -> CommodityCollection:
    """Returns a collection with all commodities for complex scenario
    testing."""
    return create_collection(commodities)


@pytest.fixture
def collection_spanned(commodities_spanned) -> CommodityCollection:
    """
    Retruns a collection with the spanned commodities.

    See the docs for the commodities_spanned fixture above for details.
    """
    return create_collection(commodities_spanned)


@pytest.fixture
def scenario_1(commodities) -> TScenario:
    """
    Returns the setup for scenario 1 in ADR13.

    See the module-level docs for details on scenario setups.
    """
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
    """
    Returns the setup for scenario 2 in ADR13.

    See the module-level docs for details on scenario setups.
    """
    collection = copy(collection_basic)

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
    """
    Returns the setup for scenario 3 in ADR13.

    See the module-level docs for details on scenario setups.
    """
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
    """
    Returns the setup for scenario 4 in ADR13.

    See the module-level docs for details on scenario setups.
    """
    collection = copy(collection_basic)

    current = collection.get_commodity("9999.20")

    attrs = dict(valid_between=date_ranges.overlap_normal_same_year)
    candidate = copy_commodity(current, transaction_pool, **attrs)

    attrs = dict(valid_between=date_ranges.normal)
    create_dependent_measure(candidate, transaction_pool, **attrs)
    create_footnote_association(candidate, transaction_pool, **attrs)

    attrs = dict(valid_between=date_ranges.overlap_normal_earlier)
    create_dependent_measure(candidate, transaction_pool, **attrs)
    create_footnote_association(candidate, transaction_pool, **attrs)

    change = CommodityChange(
        collection=collection,
        current=current,
        candidate=candidate,
        update_type=UpdateType.UPDATE,
    )

    return (collection, [change])


@pytest.fixture
def scenario_5(collection_basic, commodities, transaction_pool) -> TScenario:
    """
    Returns the setup for scenario 5 in ADR13.

    See the module-level docs for details on scenario setups.
    """
    collection = copy(collection_basic)

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
def scenario_6(collection_basic, transaction_pool, workbasket) -> TScenario:
    """
    Returns the setup for scenario 6 in ADR13.

    See the module-level docs for details on scenario setups.
    """
    collection = copy(collection_basic)
    current = collection.get_commodity("9999.20")

    attrs = dict(indent=current.indent + 1, item_id="9999201000")
    candidate = copy_commodity(current, transaction_pool, **attrs)

    measure_type = create_record(
        transaction_pool,
        factories.MeasureTypeFactory,
        measure_explosion_level=6,
    )
    delayed_transaction = factories.TransactionFactory.create(
        workbasket=workbasket,
    )
    attrs = dict(
        transaction=delayed_transaction,
        measure_type=measure_type,
    )
    create_dependent_measure(candidate, transaction_pool, **attrs)

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
    """
    Returns the setup for scenario 7 in ADR13.

    See the module-level docs for details on scenario setups.
    """
    keys = [
        "9999_80_1",
        "9999.10_80_2",
        "9999.20_80_2",
        "9999.20.00.10_80_3",
    ]
    collection = create_collection(commodities, keys)

    current = collection.get_commodity("9999.20")
    candidate = copy_commodity(
        current,
        transaction_pool,
        indent=current.indent + 1,
    )

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
    """
    Returns the setup for scenario 8 in ADR13.

    See the module-level docs for details on scenario setups.
    """
    collection, changes = scenario_7
    collection.update(changes)

    current = collection.get_commodity("9999.20")
    candidate = copy_commodity(
        current,
        transaction_pool,
        indent=current.indent - 1,
    )

    changes = [
        CommodityChange(
            collection=collection,
            current=current,
            candidate=candidate,
            update_type=UpdateType.UPDATE,
        ),
    ]

    return (collection, changes)
