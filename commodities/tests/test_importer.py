from datetime import date

import pytest
from dateutil.relativedelta import relativedelta

from commodities import models
from commodities import serializers
from common.tests import factories
from common.util import TaricDateRange
from common.validators import UpdateType
from importer.reports import CommodityChangeReports

pytestmark = pytest.mark.django_db


def test_goods_nomenclature_importer(imported_fields_match, mocked_responses):
    assert imported_fields_match(
        factories.GoodsNomenclatureFactory,
        serializers.GoodsNomenclatureSerializer,
    )


def test_goods_nomenclature_description_importer(
    imported_fields_match,
    mocked_responses,
):
    assert imported_fields_match(
        factories.GoodsNomenclatureDescriptionFactory,
        serializers.GoodsNomenclatureDescriptionSerializer,
        dependencies={
            "described_goods_nomenclature": factories.GoodsNomenclatureFactory,
        },
    )


def test_goods_nomenclature_origin_importer(
    update_type,
    date_ranges,
    imported_fields_match,
    mocked_responses,
):
    origin = factories.GoodsNomenclatureFactory.create(
        update_type=UpdateType.CREATE.value,
        valid_between=date_ranges.big,
        origin__derived_from_goods_nomenclature__valid_between=date_ranges.adjacent_earlier_big,
    )
    good = factories.GoodsNomenclatureFactory.create(
        update_type=UpdateType.CREATE.value,
        origin=None,
    )

    assert imported_fields_match(
        factories.GoodsNomenclatureOriginFactory,
        serializers.GoodsNomenclatureOriginSerializer,
        dependencies={
            "derived_from_goods_nomenclature": origin,
            "new_goods_nomenclature": good,
        },
    )

    db_good = models.GoodsNomenclature.objects.get(sid=good.sid)
    origins = models.GoodsNomenclatureOrigin.objects.filter(
        new_goods_nomenclature=db_good,
    ).latest_approved()
    if update_type == UpdateType.DELETE:
        assert not origins.exists()
    else:
        assert origins.get().derived_from_goods_nomenclature == origin


def test_goods_nomenclature_successor_importer_create(
    run_xml_import,
    date_ranges,
    mocked_responses,
):

    good = factories.GoodsNomenclatureFactory(
        update_type=UpdateType.CREATE.value,
        valid_between=date_ranges.normal,
    )
    successor = factories.GoodsNomenclatureFactory(
        update_type=UpdateType.CREATE.value,
        valid_between=date_ranges.adjacent_later,
    )

    run_xml_import(
        lambda: factories.GoodsNomenclatureSuccessorFactory.build(
            replaced_goods_nomenclature=good,
            absorbed_into_goods_nomenclature=successor,
            update_type=UpdateType.CREATE.value,
        ),
        serializers.GoodsNomenclatureSuccessorSerializer,
    )

    db_link = models.GoodsNomenclatureSuccessor.objects.get(
        replaced_goods_nomenclature__sid=good.sid,
    )
    assert db_link

    db_good = models.GoodsNomenclature.objects.get(sid=good.sid)
    assert db_good.successors.get() == successor


def test_goods_nomenclature_successor_importer_delete(
    run_xml_import,
    date_ranges,
    mocked_responses,
):
    good = factories.GoodsNomenclatureFactory(
        update_type=UpdateType.CREATE.value,
        valid_between=date_ranges.normal,
    )
    successor = factories.GoodsNomenclatureFactory(
        update_type=UpdateType.CREATE.value,
        valid_between=date_ranges.adjacent_later,
    )
    factories.GoodsNomenclatureSuccessorFactory(
        replaced_goods_nomenclature=good,
        absorbed_into_goods_nomenclature=successor,
        update_type=UpdateType.CREATE.value,
    )

    updated_good = factories.GoodsNomenclatureFactory(
        sid=good.sid,
        item_id=good.item_id,
        suffix=good.suffix,
        version_group=good.version_group,
        update_type=UpdateType.UPDATE.value,
        valid_between=date_ranges.no_end,
    )

    run_xml_import(
        lambda: factories.GoodsNomenclatureSuccessorFactory.build(
            replaced_goods_nomenclature=updated_good,
            absorbed_into_goods_nomenclature=successor,
            update_type=UpdateType.DELETE.value,
        ),
        serializers.GoodsNomenclatureSuccessorSerializer,
    )

    db_link = models.GoodsNomenclatureSuccessor.objects.filter(
        replaced_goods_nomenclature__sid=good.sid,
    )
    assert not db_link.latest_approved().exists()
    assert db_link.latest_deleted().exists()


def test_goods_nomenclature_indent_importer(imported_fields_match):
    db_indent = imported_fields_match(
        factories.GoodsNomenclatureIndentFactory,
        serializers.GoodsNomenclatureIndentSerializer,
        dependencies={
            "indented_goods_nomenclature": factories.SimpleGoodsNomenclatureFactory(
                item_id="1100000000",
            ),
        },
    )

    assert db_indent.indent == 0
    assert db_indent.nodes.count() == 1
    assert db_indent.nodes.first().depth == 1
    assert db_indent.nodes.first().get_parent() is None


def test_goods_nomenclature_indent_importer_with_parent_low_indent(
    imported_fields_match,
    mocked_responses,
):
    parent_indent = factories.GoodsNomenclatureIndentFactory.create(
        indented_goods_nomenclature__item_id="1200000000",
    ).nodes.first()

    db_indent = imported_fields_match(
        factories.GoodsNomenclatureIndentFactory,
        serializers.GoodsNomenclatureIndentSerializer,
        dependencies={
            "indent": 0,
            "indented_goods_nomenclature": factories.SimpleGoodsNomenclatureFactory(
                item_id="1201000000",
            ),
        },
    )

    assert db_indent.indent == 0
    assert db_indent.nodes.count() == 1
    assert db_indent.nodes.first().depth == 2
    assert db_indent.nodes.first().get_parent() == parent_indent


def test_goods_nomenclature_indent_importer_with_parent_high_indent(
    imported_fields_match,
    mocked_responses,
):
    """Ensure Goods Nomenclature Indent importers can appropriately handle
    importing indents into the hierarchy when receiving codes which have already
    used up all 10 digits of the code."""
    parent_indent = None

    # Make enough of a hierarchy to ensure we're beyond indent 5, meaning we're dependent
    # on suffix, indent and code and not just the goods code to figure out the hierarchy.
    for idx in range(1, 6):
        parent_indent = factories.GoodsNomenclatureIndentNodeFactory.create(
            indent__indented_goods_nomenclature__item_id=("12" * idx).ljust(10, "0"),
            parent=parent_indent,
        )

    db_indent = imported_fields_match(
        factories.GoodsNomenclatureIndentFactory,
        serializers.GoodsNomenclatureIndentSerializer,
        dependencies={
            "indent": 4,
            "indented_goods_nomenclature": factories.GoodsNomenclatureFactory(
                item_id="1212121215",
            ),
        },
    )

    assert db_indent.indent == 4
    assert db_indent.nodes.count() == 1
    assert db_indent.nodes.first().depth == 6
    assert db_indent.nodes.first().get_parent() == parent_indent


def test_goods_nomenclature_indent_importer_multiple_parents(
    imported_fields_match,
    date_ranges,
    mocked_responses,
):
    """
    In some cases there is an indent which is created which already expects to
    have multiple parents over its lifetime.

    Assert multiple indent nodes are generated in this scenario.
    """

    indent_validity = TaricDateRange(
        date_ranges.adjacent_earlier.lower,
        date_ranges.adjacent_later.upper,
    )
    parent_indent = factories.SimpleGoodsNomenclatureIndentFactory.create(
        validity_start=indent_validity.lower,
        indented_goods_nomenclature__valid_between=indent_validity,
        indented_goods_nomenclature__item_id="1300000000",
    )
    parent_nodes = {
        factories.GoodsNomenclatureIndentNodeFactory.create(
            valid_between=date_ranges.adjacent_earlier,
            indent=parent_indent,
        ),
        factories.GoodsNomenclatureIndentNodeFactory.create(
            valid_between=date_ranges.normal,
            indent=parent_indent,
        ),
        factories.GoodsNomenclatureIndentNodeFactory.create(
            valid_between=date_ranges.adjacent_later,
            indent=parent_indent,
        ),
    }

    db_indent = imported_fields_match(
        factories.GoodsNomenclatureIndentFactory,
        serializers.GoodsNomenclatureIndentSerializer,
        dependencies={
            "indent": 0,
            "indented_goods_nomenclature": factories.SimpleGoodsNomenclatureFactory(
                item_id="1301000000",
                valid_between=indent_validity,
            ),
            "validity_start": indent_validity.lower,
        },
    )

    assert db_indent.indent == 0
    assert db_indent.nodes.count() == 3

    first_parents = {node.get_parent() for node in db_indent.nodes.all()}
    assert first_parents == parent_nodes


@pytest.mark.parametrize("update_type", [UpdateType.UPDATE, UpdateType.DELETE])
def test_goods_nomenclature_indent_importer_update_multiple_parents(
    run_xml_import,
    mocked_responses,
    update_type,
):
    parent_indent = factories.SimpleGoodsNomenclatureIndentFactory.create(
        validity_start=date(2020, 1, 1),
        indented_goods_nomenclature__valid_between=TaricDateRange(
            date(2020, 1, 1),
            date(2020, 12, 1),
        ),
        indented_goods_nomenclature__item_id="1300000000",
    )
    parent1 = factories.GoodsNomenclatureIndentNodeFactory.create(
        valid_between=TaricDateRange(date(2020, 1, 1), date(2020, 4, 1)),
        indent=parent_indent,
    )
    parent2 = factories.GoodsNomenclatureIndentNodeFactory.create(
        valid_between=TaricDateRange(date(2020, 4, 2), date(2020, 8, 1)),
        indent=parent_indent,
    )
    parent3 = factories.GoodsNomenclatureIndentNodeFactory.create(
        valid_between=TaricDateRange(date(2020, 8, 2), date(2020, 12, 1)),
        indent=parent_indent,
    )

    child = factories.SimpleGoodsNomenclatureFactory.create(
        item_id="1301000000",
        valid_between=TaricDateRange(date(2020, 1, 1), date(2020, 12, 1)),
    )
    first_indent = run_xml_import(
        lambda: factories.GoodsNomenclatureIndentFactory.build(
            indented_goods_nomenclature=child,
            validity_start=date(2020, 1, 1),
            indent=0,
        ),
        serializers.GoodsNomenclatureIndentSerializer,
    )
    first_parents = [node.get_parent() for node in first_indent.nodes.all()]

    assert set(first_parents) == {parent1, parent2, parent3}

    second_indent = run_xml_import(
        lambda: factories.GoodsNomenclatureIndentFactory.build(
            sid=first_indent.sid,
            indented_goods_nomenclature=first_indent.indented_goods_nomenclature,
            validity_start=date(2020, 6, 2),
            update_type=update_type,
            indent=0,
        ),
        serializers.GoodsNomenclatureIndentSerializer,
    )
    second_parents = [node.get_parent() for node in second_indent.nodes.all()]

    assert second_indent.sid == first_indent.sid
    assert second_indent.indent == 0
    assert len(second_parents) == 2
    assert set(second_parents) == {parent2, parent3}


@pytest.mark.parametrize("item_id,suffix", [("1402000000", "80"), ("1401010000", "20")])
def test_goods_nomenclature_indent_importer_with_triple_00_indent(
    imported_fields_match,
    mocked_responses,
    item_id,
    suffix,
):
    """
    In cases where there are phantom headers right below a chapter (regardless
    of whether the good is directly within its lineage) some goods are still
    given a "00" indent, despite being 3 levels into the hierarchy.

    Assert that this edgecase is handled.
    """
    parent_indent = factories.GoodsNomenclatureIndentFactory.create(
        indented_goods_nomenclature__item_id="1401000000",
        indented_goods_nomenclature__suffix="20",
        node__parent=factories.GoodsNomenclatureIndentFactory.create(
            indented_goods_nomenclature__item_id="1400000000",
        ).nodes.first(),
    ).nodes.first()

    db_indent = imported_fields_match(
        factories.GoodsNomenclatureIndentFactory,
        serializers.GoodsNomenclatureIndentSerializer,
        dependencies={
            "node": None,
            "indent": 0,
            "indented_goods_nomenclature": factories.SimpleGoodsNomenclatureFactory(
                item_id=item_id,
                suffix=suffix,
            ),
        },
    )

    assert db_indent.indent == 0
    assert db_indent.nodes.count() == 1
    assert db_indent.nodes.first().depth == 3
    assert db_indent.nodes.first().get_parent() == parent_indent
    assert db_indent.indented_goods_nomenclature.indents.count() == (
        2 if db_indent.update_type != UpdateType.CREATE else 1
    )


def test_goods_nomenclature_indent_importer_create_out_of_order(
    run_xml_import,
    mocked_responses,
):
    """
    This test checks that if indents are loaded out of order (i.e. children
    first) then when the actual parents are loaded they will correctly inherit
    the children and nodes will be removed from any of the previous parents.

    Observed in the wild:

        Goods nomenclature:  0106900010 created in txn 294652
            Goods Nomenclature Indent: 2 - 0106900010 valid: [2021-01-01, None) txn: 294652
        Goods nomenclature:  0106900010 created in txn 294651
            Goods Nomenclature Indent: 3 - 0106900010 valid: [2021-01-01, None) txn: 294651
        Goods nomenclature:  0106900019 created in txn 294650
            Goods Nomenclature Indent: 3 - 0106900019 valid: [2021-01-01, None) txn: 294650
    """

    root_indent = factories.GoodsNomenclatureIndentFactory.create(
        indented_goods_nomenclature__item_id="7700000000",
        indented_goods_nomenclature__suffix="80",
    )

    not_parent = factories.GoodsNomenclatureIndentFactory.create(
        indented_goods_nomenclature__item_id="7710000000",
        indented_goods_nomenclature__suffix="80",
        node__parent=root_indent.nodes.first(),
    )

    child2 = factories.SimpleGoodsNomenclatureFactory.create(
        item_id="7790000000",
        suffix="80",
    )
    db_child2_indent = run_xml_import(
        lambda: factories.GoodsNomenclatureIndentFactory.build(
            indented_goods_nomenclature=child2,
            indent=1,
        ),
        serializers.GoodsNomenclatureIndentSerializer,
    )
    assert db_child2_indent.nodes.get().get_parent() == not_parent.nodes.get()

    child1 = factories.SimpleGoodsNomenclatureFactory.create(
        item_id="7720000000",
        suffix="80",
    )
    db_child1_indent = run_xml_import(
        lambda: factories.GoodsNomenclatureIndentFactory.build(
            indented_goods_nomenclature=child1,
            indent=1,
        ),
        serializers.GoodsNomenclatureIndentSerializer,
    )
    assert db_child1_indent.nodes.get().get_parent() == not_parent.nodes.get()

    parent = factories.SimpleGoodsNomenclatureFactory.create(
        item_id="7720000000",
        suffix="10",
    )
    db_parent_indent = run_xml_import(
        lambda: factories.GoodsNomenclatureIndentFactory.build(
            indented_goods_nomenclature=parent,
            indent=0,
        ),
        serializers.GoodsNomenclatureIndentSerializer,
    )

    assert db_parent_indent.nodes.get().get_parent() == root_indent.nodes.get()
    assert db_child1_indent.nodes.get().get_parent() == db_parent_indent.nodes.get()
    assert db_child2_indent.nodes.get().get_parent() == db_parent_indent.nodes.get()
    assert not not_parent.nodes.get().get_descendants().exists()


@pytest.fixture
def make_inappropriate_family(date_ranges):
    def _make_inappropriate_family(chapter):
        grand_parent_indent = factories.GoodsNomenclatureIndentFactory.create(
            indented_goods_nomenclature__item_id=f"{chapter}00000000",
            indented_goods_nomenclature__valid_between=date_ranges.no_end,
            validity_start=date_ranges.no_end.lower,
            indent="0",
            node__valid_between=date_ranges.no_end,
        )

        bad_parent = factories.GoodsNomenclatureIndentFactory.create(
            node__parent=grand_parent_indent.nodes.first(),
            indented_goods_nomenclature__item_id=f"{chapter}01000000",
            indented_goods_nomenclature__valid_between=date_ranges.no_end,
            validity_start=date_ranges.no_end.lower,
            indent="0",
            node__valid_between=date_ranges.no_end,
        )

        child_indent = factories.GoodsNomenclatureIndentFactory.create(
            node__parent=bad_parent.nodes.first(),
            validity_start=date_ranges.no_end.lower,
            indent="1",
            indented_goods_nomenclature=factories.GoodsNomenclatureFactory.create(
                item_id=f"{chapter}02020000",
                valid_between=date_ranges.no_end,
            ),
        )

        return bad_parent, child_indent

    return _make_inappropriate_family


def test_goods_nomenclature_indent_importer_with_branch_shift(
    make_inappropriate_family,
    imported_fields_match,
    date_ranges,
    mocked_responses,
):
    """
    In some scenarios a new indent can step in between an existing Goods
    Nomenclature and its parent.

    This would require the tree to be updated once ingested so as to shift all
    children to the new indent.
    """

    bad_parent, child_indent = make_inappropriate_family("45")

    grand_child_indent = factories.GoodsNomenclatureIndentFactory.create(
        node__parent=child_indent.nodes.first(),
        validity_start=date_ranges.no_end.lower,
        indent="2",
        indented_goods_nomenclature=factories.GoodsNomenclatureFactory.create(
            item_id="4502020000",
            valid_between=date_ranges.no_end,
        ),
    )

    child_nodes = models.GoodsNomenclatureIndentNode.objects.filter(indent=child_indent)
    assert child_nodes.count() > 0
    for node in child_nodes:
        assert node.get_parent() == bad_parent.nodes.first()

    grandchild_nodes = models.GoodsNomenclatureIndentNode.objects.filter(
        indent=grand_child_indent,
    )
    assert grandchild_nodes.count() > 0
    for node in grandchild_nodes:
        assert node.get_parent().indent == child_indent

    new_parent_node = imported_fields_match(
        factories.GoodsNomenclatureIndentFactory,
        serializers.GoodsNomenclatureIndentSerializer,
        dependencies={
            "indented_goods_nomenclature": factories.GoodsNomenclatureFactory(
                item_id="4502000000",
                valid_between=date_ranges.no_end,
            ),
            "validity_start": date_ranges.no_end.lower,
            "indent": 0,
        },
    ).nodes.first()

    child_nodes = models.GoodsNomenclatureIndentNode.objects.filter(indent=child_indent)
    grand_child_nodes = models.GoodsNomenclatureIndentNode.objects.filter(
        indent=grand_child_indent,
    )
    assert child_nodes.count() > 0
    for node in child_nodes:
        assert node.get_parent() == new_parent_node

    assert grand_child_nodes.count() > 0
    for node in grand_child_nodes:
        assert node.get_parent().indent == child_indent


def test_goods_nomenclature_indent_importer_with_overlapping_branch_shift(
    make_inappropriate_family,
    imported_fields_match,
    date_ranges,
    mocked_responses,
):
    """
    In some scenarios a new indent can step in between an existing Goods
    Nomenclature and its parent. In more extreme cases when this happens the
    dates could overlap so that the child needs to belong to both parents.

    Ensure when this happens the child is split between both parents.
    """
    bad_parent, child_indent = make_inappropriate_family("46")

    child_nodes = models.GoodsNomenclatureIndentNode.objects.filter(indent=child_indent)
    assert child_nodes.count() > 0
    for node in child_nodes:
        assert node.get_parent() == bad_parent.nodes.first()

    new_parent = imported_fields_match(
        factories.GoodsNomenclatureIndentFactory,
        serializers.GoodsNomenclatureIndentSerializer,
        dependencies={
            "indented_goods_nomenclature": factories.GoodsNomenclatureFactory(
                item_id="4602000000",
                valid_between=date_ranges.adjacent_no_end,
            ),
            "validity_start": date_ranges.adjacent_no_end.lower,
            "indent": 0,
        },
    )

    child_nodes = models.GoodsNomenclatureIndentNode.objects.filter(indent=child_indent)

    assert child_nodes.count() == 2
    nodes = {node.get_parent().indent: node for node in child_nodes}

    assert bad_parent in nodes
    assert nodes[bad_parent].valid_between == TaricDateRange(
        date_ranges.no_end.lower,
        date_ranges.adjacent_no_end.lower - relativedelta(days=1),
    )

    assert new_parent in nodes
    assert nodes[new_parent].valid_between == date_ranges.adjacent_no_end


@pytest.mark.parametrize("update_type", [UpdateType.UPDATE, UpdateType.DELETE])
def test_goods_nomenclature_indent_importer_update_with_children(
    run_xml_import,
    mocked_responses,
    update_type,
    date_ranges,
):
    parent_indent = factories.GoodsNomenclatureIndentFactory.create(
        indented_goods_nomenclature__item_id="4400000000",
        validity_start=date_ranges.no_end.lower,
    )

    indent = factories.GoodsNomenclatureIndentFactory.create(
        node__parent=parent_indent.nodes.first(),
        indented_goods_nomenclature__item_id="4401000000",
        validity_start=date_ranges.no_end.lower,
    )

    indent_node = indent.nodes.first()

    child_indent_nodes = {
        factories.GoodsNomenclatureIndentFactory.create(
            indented_goods_nomenclature__item_id=f"44010{idx}0000",
            node__parent=indent_node,
            validity_start=date_ranges.no_end.lower,
        ).nodes.first()
        for idx in range(1, 6)
    }

    db_indent = run_xml_import(
        lambda: factories.GoodsNomenclatureIndentFactory.build(
            sid=indent.sid,
            indent=0,
            indented_goods_nomenclature=indent.indented_goods_nomenclature,
            validity_start=date_ranges.adjacent_no_end.lower,
            update_type=update_type,
        ),
        serializers.GoodsNomenclatureIndentSerializer,
    )

    assert db_indent.indent == 0
    assert db_indent.nodes.count() == 1
    assert db_indent.nodes.first().depth == 2

    db_indent_node = db_indent.nodes.first()
    children = db_indent_node.get_children()
    assert children.count() == 5

    assert any(
        child.valid_between.lower == indent.validity_start
        for child in child_indent_nodes
    )
    assert not any(
        child.valid_between.lower == indent.validity_start for child in children
    )
    assert {child.indent for child in children} == {
        child.indent for child in child_indent_nodes
    }


def test_footnote_association_goods_nomenclature_importer(imported_fields_match):
    assert imported_fields_match(
        factories.FootnoteAssociationGoodsNomenclatureFactory,
        serializers.FootnoteAssociationGoodsNomenclatureSerializer,
        dependencies={
            "goods_nomenclature": factories.GoodsNomenclatureFactory,
            "associated_footnote": factories.FootnoteFactory,
        },
    )


@pytest.mark.parametrize(
    (
        "current_indent_start_date,"
        "imported_indent_start_date,"
        "curent_node_end_date,"
        "imported_node_end_date"
    ),
    (
        (
            date.today() + relativedelta(months=-1),
            date.today() + relativedelta(months=+1),
            date.today() + relativedelta(months=+1, days=-1),
            None,
        ),
        (
            date.today() + relativedelta(months=+1),
            date.today() + relativedelta(months=-1),
            None,
            date.today() + relativedelta(months=+1, days=-1),
        ),
        (
            None,
            date.today() + relativedelta(months=-1),
            None,
            None,
        ),
    ),
    ids=(
        "preceding_indent",
        "succeeding_indent",
        "no_adjacent_indents",
    ),
)
def test_sync_indent_node_end_dates_on_indent_import(
    run_xml_import,
    current_indent_start_date,
    imported_indent_start_date,
    curent_node_end_date,
    imported_node_end_date,
):
    """
    Asserts that indent node end dates are synced on new indent imports.

    This unit test covers three scenarios:
    - preceding indent: the imported indent has a preceding indent,
      in which case the node on the preceding indent needs to be end-dated
    - succeeding indent: the imported indent has a succeeding indent,
      in which case the node on the importend indent needs to be end-dated
    - no adjacent indents: the imported indent has no adjacent indents,
      in which case no action is needed and its node's end-date should be None
    """
    good = factories.SimpleGoodsNomenclatureFactory.create(
        item_id="1200000000",
        suffix="80",
    )

    if current_indent_start_date:
        current_indent = run_xml_import(
            lambda: factories.GoodsNomenclatureIndentFactory.build(
                validity_start=current_indent_start_date,
                indented_goods_nomenclature=good,
                indent=0,
            ),
            serializers.GoodsNomenclatureIndentSerializer,
        )

    imported_indent = run_xml_import(
        lambda: factories.GoodsNomenclatureIndentFactory.build(
            validity_start=imported_indent_start_date,
            indented_goods_nomenclature=good,
            indent=0,
        ),
        serializers.GoodsNomenclatureIndentSerializer,
    )

    if current_indent_start_date:
        current_node = current_indent.nodes.order_by("creating_transaction_id").last()
        assert current_node.valid_between.upper == curent_node_end_date

    imported_node = imported_indent.nodes.first()
    assert imported_node.valid_between.upper == imported_node_end_date


def test_future_affected_measures_are_detected(
    run_xml_import,
    date_ranges,
):
    attrs = dict(
        item_id="1199102030",
        suffix="80",
    )

    good = factories.GoodsNomenclatureFactory.create(
        valid_between=date_ranges.no_end, **attrs
    )
    future_measure = factories.MeasureFactory(
        goods_nomenclature=good,
        valid_between=date_ranges.adjacent_even_later,
    )

    imported_good = run_xml_import(
        lambda: factories.GoodsNomenclatureFactory.build(
            valid_between=date_ranges.normal, update_type=UpdateType.UPDATE, **attrs
        ),
        serializers.GoodsNomenclatureSerializer,
    )

    workbasket = imported_good.transaction.workbasket
    reports = CommodityChangeReports(workbasket)
    affected_measures = reports.affected_measures
    affected_measures_sids = [m.sid for m in affected_measures]
    assert future_measure in affected_measures_sids
