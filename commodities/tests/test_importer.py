from datetime import date

import pytest
from dateutil.relativedelta import relativedelta

from commodities import models
from commodities import serializers
from common.tests import factories
from common.tests.util import generate_test_import_xml
from common.util import TaricDateRange
from common.validators import UpdateType
from importer.taric import process_taric_xml_stream
from workbaskets.validators import WorkflowStatus

pytestmark = pytest.mark.django_db


def compare_indent(indent, db_indent, indent_level, count, depth):
    assert db_indent.sid == indent.sid
    assert db_indent.indent == indent_level
    assert db_indent.nodes.count() == count
    assert db_indent.nodes.first().depth == depth
    assert (
        db_indent.indented_goods_nomenclature.sid
        == indent.indented_goods_nomenclature.sid
    )
    assert db_indent.validity_start == indent.validity_start


def compare_updated_indent(
    updated_indent,
    db_indent,
    indent_level,
    count,
    depth,
    parent_indent=None,
):
    db_indent_node = db_indent.nodes.first()

    assert db_indent.indented_goods_nomenclature.indents.count() == 2

    compare_indent(updated_indent, db_indent, indent_level, count, depth)

    if parent_indent:
        assert db_indent_node.get_parent() == parent_indent

    version_group = db_indent.version_group
    version_group.refresh_from_db()
    assert version_group.versions.count() == 2
    assert version_group == db_indent.version_group
    assert version_group.current_version == db_indent
    assert version_group.current_version.update_type == updated_indent.update_type


def make_and_get_indent(indent, valid_user, depth):
    data = {
        "indented_goods_nomenclature": {
            "sid": indent.indented_goods_nomenclature.sid,
            "item_id": indent.indented_goods_nomenclature.item_id,
            "suffix": indent.indented_goods_nomenclature.suffix,
        },
        "taric_template": "taric/goods_nomenclature_indent.xml",
        "update_type": indent.update_type,
        "sid": indent.sid,
        "start_date": f"{indent.validity_start:%Y-%m-%d}",
        "indent": depth,
    }

    xml = generate_test_import_xml(data)

    process_taric_xml_stream(
        xml,
        username=valid_user.username,
        status=WorkflowStatus.PUBLISHED.value,
    )

    return models.GoodsNomenclatureIndent.objects.filter(
        sid=indent.sid,
    ).last()


def test_goods_nomenclature_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.GoodsNomenclatureFactory,
        serializers.GoodsNomenclatureSerializer,
    )


def test_goods_nomenclature_importer_update(update_imported_fields_match):
    assert update_imported_fields_match(
        factories.GoodsNomenclatureFactory,
        serializers.GoodsNomenclatureSerializer,
    )


def test_goods_nomenclature_description_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.GoodsNomenclatureDescriptionFactory.build(
            described_goods_nomenclature=factories.GoodsNomenclatureFactory.create(),
        ),
        serializers.GoodsNomenclatureDescriptionSerializer,
    )


def test_goods_nomenclature_description_importer_update(update_imported_fields_match):
    assert update_imported_fields_match(
        factories.GoodsNomenclatureDescriptionFactory,
        serializers.GoodsNomenclatureDescriptionSerializer,
        dependencies={
            "described_goods_nomenclature": factories.GoodsNomenclatureFactory,
        },
    )


def test_goods_nomenclature_origin_importer_create(valid_user, date_ranges):
    origin = factories.GoodsNomenclatureFactory.create(
        update_type=UpdateType.CREATE.value,
        valid_between=date_ranges.big,
        origin__derived_from_goods_nomenclature__valid_between=date_ranges.adjacent_earlier_big,
    )
    good = factories.GoodsNomenclatureFactory.create(
        update_type=UpdateType.CREATE.value,
        origin=None,
    )
    origin_link = factories.GoodsNomenclatureOriginFactory.build(
        derived_from_goods_nomenclature=origin,
        new_goods_nomenclature=good,
        update_type=UpdateType.CREATE.value,
    )

    xml = generate_test_import_xml(
        serializers.GoodsNomenclatureOriginSerializer(
            origin_link,
            context={"format": "xml"},
        ).data,
    )

    process_taric_xml_stream(
        xml,
        username=valid_user.username,
        status=WorkflowStatus.PUBLISHED.value,
    )

    db_link = models.GoodsNomenclatureOrigin.objects.get(
        new_goods_nomenclature__sid=good.sid,
    )
    assert db_link

    db_good = models.GoodsNomenclature.objects.get(sid=good.sid)
    assert db_good.origins.get() == origin


def test_goods_nomenclature_successor_importer_create(valid_user, date_ranges):
    good = factories.GoodsNomenclatureFactory(
        update_type=UpdateType.CREATE.value,
        valid_between=date_ranges.normal,
    )
    successor = factories.GoodsNomenclatureFactory(
        update_type=UpdateType.CREATE.value,
        valid_between=date_ranges.adjacent_later,
    )
    successor_link = factories.GoodsNomenclatureSuccessorFactory.build(
        replaced_goods_nomenclature=good,
        absorbed_into_goods_nomenclature=successor,
        update_type=UpdateType.CREATE.value,
    )

    xml = generate_test_import_xml(
        serializers.GoodsNomenclatureSuccessorSerializer(
            successor_link,
            context={"format": "xml"},
        ).data,
    )

    process_taric_xml_stream(
        xml,
        username=valid_user.username,
        status=WorkflowStatus.PUBLISHED.value,
    )

    db_link = models.GoodsNomenclatureSuccessor.objects.get(
        replaced_goods_nomenclature__sid=good.sid,
    )
    assert db_link

    db_good = models.GoodsNomenclature.objects.get(sid=good.sid)
    assert db_good.successors.get() == successor


def test_goods_nomenclature_successor_importer_delete(valid_user, date_ranges):
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

    successor_link = factories.GoodsNomenclatureSuccessorFactory.build(
        replaced_goods_nomenclature=updated_good,
        absorbed_into_goods_nomenclature=successor,
        update_type=UpdateType.DELETE.value,
    )

    xml = generate_test_import_xml(
        serializers.GoodsNomenclatureSuccessorSerializer(
            successor_link,
            context={"format": "xml"},
        ).data,
    )

    process_taric_xml_stream(
        xml,
        username=valid_user.username,
        status=WorkflowStatus.PUBLISHED.value,
    )

    db_link = models.GoodsNomenclatureSuccessor.objects.filter(
        replaced_goods_nomenclature__sid=good.sid,
    )
    assert not db_link.latest_approved().exists()
    assert db_link.latest_deleted().exists()


def test_goods_nomenclature_indent_importer_create(valid_user):
    indent = factories.GoodsNomenclatureIndentFactory.build(
        update_type=UpdateType.CREATE.value,
        indented_goods_nomenclature=factories.SimpleGoodsNomenclatureFactory.create(
            item_id="1100000000",
        ),
    )

    db_indent = make_and_get_indent(indent, valid_user, depth=0)

    compare_indent(indent, db_indent, indent_level=0, count=1, depth=1)


@pytest.mark.parametrize("update_type", [UpdateType.UPDATE, UpdateType.DELETE])
def test_goods_nomenclature_indent_importer_update(
    valid_user,
    date_ranges,
    update_type,
):
    indent = factories.GoodsNomenclatureIndentFactory.create(
        indented_goods_nomenclature=factories.SimpleGoodsNomenclatureFactory.create(
            item_id="2100000000",
        ),
        validity_start=date_ranges.normal.lower,
    )

    updated_indent = factories.GoodsNomenclatureIndentFactory.build(
        sid=indent.sid,
        indented_goods_nomenclature=indent.indented_goods_nomenclature,
        update_type=update_type,
        validity_start=date_ranges.adjacent_no_end.lower,
    )

    db_indent = make_and_get_indent(updated_indent, valid_user, depth=0)

    compare_updated_indent(updated_indent, db_indent, indent_level=0, count=1, depth=1)


def test_goods_nomenclature_indent_importer_create_with_parent_low_indent(valid_user):
    parent_indent = factories.GoodsNomenclatureIndentFactory.create(
        indented_goods_nomenclature__item_id="1200000000",
    ).nodes.first()

    indent = factories.GoodsNomenclatureIndentFactory.build(
        indented_goods_nomenclature=factories.SimpleGoodsNomenclatureFactory.create(
            item_id="1201000000",
        ),
    )

    db_indent = make_and_get_indent(indent, valid_user, depth=0)

    db_indent_node = db_indent.nodes.first()

    compare_indent(indent, db_indent, indent_level=0, count=1, depth=2)
    assert db_indent_node.get_parent() == parent_indent


@pytest.mark.parametrize("update_type", [UpdateType.UPDATE, UpdateType.DELETE])
def test_goods_nomenclature_indent_importer_update_with_parent_low_indent(
    valid_user,
    date_ranges,
    update_type,
):
    parent_indent = factories.GoodsNomenclatureIndentFactory.create(
        indented_goods_nomenclature__item_id="1200000000",
    ).nodes.first()

    indent = factories.GoodsNomenclatureIndentFactory.create(
        indented_goods_nomenclature=factories.SimpleGoodsNomenclatureFactory.create(
            item_id="1201000000",
        ),
        node__parent=parent_indent,
        validity_start=date_ranges.normal.lower,
    )

    updated_indent = factories.GoodsNomenclatureIndentFactory.build(
        sid=indent.sid,
        indented_goods_nomenclature=indent.indented_goods_nomenclature,
        validity_start=date_ranges.adjacent_no_end.lower,
        update_type=update_type,
    )

    db_indent = make_and_get_indent(updated_indent, valid_user, depth=0)
    compare_updated_indent(
        updated_indent,
        db_indent,
        indent_level=0,
        count=1,
        depth=2,
        parent_indent=parent_indent,
    )


def test_goods_nomenclature_indent_importer_create_with_parent_high_indent(valid_user):
    """Ensure Goods Nomenclature Indent importers can appropriately handle
    importing indents into the hierarchy when receiving codes which have already
    used up all 10 digits of the code."""
    parent_indent = None
    for idx in range(1, 6):
        parent_indent = factories.GoodsNomenclatureIndentNodeFactory.create(
            indent__indented_goods_nomenclature__item_id=("12" * idx).ljust(10, "0"),
            parent=parent_indent,
        )

    indent = factories.GoodsNomenclatureIndentFactory.build(
        update_type=UpdateType.CREATE.value,
        indented_goods_nomenclature=factories.GoodsNomenclatureFactory.create(
            item_id="1212121215",
        ),
    )

    db_indent = make_and_get_indent(indent, valid_user, depth=4)

    compare_indent(indent, db_indent, indent_level=4, count=1, depth=6)


@pytest.mark.parametrize("update_type", [UpdateType.UPDATE, UpdateType.DELETE])
def test_goods_nomenclature_indent_importer_update_with_parent_high_indent(
    valid_user,
    update_type,
    date_ranges,
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

    indent = factories.GoodsNomenclatureIndentFactory.create(
        indented_goods_nomenclature=factories.GoodsNomenclatureFactory.create(
            item_id="1212121215",
        ),
        validity_start=date_ranges.normal.lower,
    )

    updated_indent = factories.GoodsNomenclatureIndentFactory.build(
        sid=indent.sid,
        indented_goods_nomenclature=indent.indented_goods_nomenclature,
        validity_start=date_ranges.adjacent_no_end.lower,
        update_type=update_type,
    )

    db_indent = make_and_get_indent(updated_indent, valid_user, depth=4)

    compare_indent(updated_indent, db_indent, indent_level=4, count=1, depth=6)


def test_goods_nomenclature_indent_importer_create_multiple_parents(
    valid_user,
    date_ranges,
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

    indent = factories.GoodsNomenclatureIndentFactory.build(
        update_type=UpdateType.CREATE.value,
        indented_goods_nomenclature=factories.SimpleGoodsNomenclatureFactory.create(
            item_id="1301000000",
            valid_between=indent_validity,
        ),
        validity_start=indent_validity.lower,
    )

    db_indent = make_and_get_indent(indent, valid_user, depth=0)

    assert db_indent.sid == indent.sid
    assert db_indent.indent == 0
    assert db_indent.nodes.count() == 3
    assert all(node.get_parent() in parent_nodes for node in db_indent.nodes.all())
    assert (
        db_indent.indented_goods_nomenclature.sid
        == indent.indented_goods_nomenclature.sid
    )
    assert db_indent.validity_start == indent.validity_start


@pytest.mark.parametrize("update_type", [UpdateType.UPDATE, UpdateType.DELETE])
def test_goods_nomenclature_indent_importer_update_multiple_parents(
    valid_user,
    date_ranges,
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

    indent = factories.GoodsNomenclatureIndentFactory.build(
        indented_goods_nomenclature=factories.SimpleGoodsNomenclatureFactory.create(
            item_id="1301000000",
            valid_between=TaricDateRange(date(2020, 1, 1), date(2020, 12, 1)),
        ),
        validity_start=date(2020, 1, 1),
    )

    first_indent = make_and_get_indent(indent, valid_user, depth=0)
    first_parents = [node.get_parent() for node in first_indent.nodes.all()]

    assert set(first_parents) == {parent1, parent2, parent3}

    updated_indent = factories.GoodsNomenclatureIndentFactory.build(
        sid=first_indent.sid,
        indented_goods_nomenclature=indent.indented_goods_nomenclature,
        validity_start=date(2020, 6, 2),
        update_type=update_type,
    )
    second_indent = make_and_get_indent(updated_indent, valid_user, depth=0)
    second_parents = [node.get_parent() for node in second_indent.nodes.all()]

    assert second_indent.sid == first_indent.sid
    assert second_indent.indent == 0
    assert len(second_parents) == 2
    assert set(second_parents) == {parent2, parent3}
    assert (
        second_indent.indented_goods_nomenclature.sid
        == indent.indented_goods_nomenclature.sid
    )
    assert second_indent.validity_start == updated_indent.validity_start


@pytest.mark.parametrize("item_id,suffix", [("1402000000", "80"), ("1401010000", "20")])
def test_goods_nomenclature_indent_importer_create_with_triple_00_indent(
    valid_user,
    item_id,
    suffix,
):
    """
    In cases where there are phantom headers right below a chapter (regardless
    of whether the good is directly within its lineage) some goods are still
    given a "00" indent, despite being 3 levels into the hierarchy.

    Assert that this edgecase is handled.
    """
    factories.GoodsNomenclatureIndentFactory.create(
        update_type=UpdateType.CREATE.value,
        indented_goods_nomenclature__item_id="1401000000",
        indented_goods_nomenclature__suffix="20",
        node__parent=factories.GoodsNomenclatureIndentFactory.create(
            indented_goods_nomenclature__item_id="1400000000",
        ).nodes.first(),
    ).nodes.first()

    indent = factories.GoodsNomenclatureIndentFactory.build(
        update_type=UpdateType.CREATE.value,
        indented_goods_nomenclature=factories.SimpleGoodsNomenclatureFactory.create(
            item_id=item_id,
            suffix=suffix,
        ),
    )

    db_indent = make_and_get_indent(indent, valid_user, depth=0)

    compare_indent(indent, db_indent, indent_level=0, count=1, depth=3)


def test_goods_nomenclature_indent_importer_create_out_of_order(valid_user):
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

    child2_indent = factories.GoodsNomenclatureIndentFactory.build(
        indented_goods_nomenclature=factories.SimpleGoodsNomenclatureFactory.create(
            item_id="7790000000",
            suffix="80",
        ),
        update_type=UpdateType.CREATE,
    )
    db_child2_indent = make_and_get_indent(child2_indent, valid_user, depth=1)
    assert db_child2_indent.nodes.get().get_parent() == not_parent.nodes.get()

    child1_indent = factories.GoodsNomenclatureIndentFactory.build(
        indented_goods_nomenclature=factories.SimpleGoodsNomenclatureFactory.create(
            item_id="7720000000",
            suffix="80",
        ),
        update_type=UpdateType.CREATE,
    )
    db_child1_indent = make_and_get_indent(child1_indent, valid_user, depth=1)
    assert db_child2_indent.nodes.get().get_parent() == not_parent.nodes.get()

    parent_indent = factories.GoodsNomenclatureIndentFactory.build(
        indented_goods_nomenclature=factories.SimpleGoodsNomenclatureFactory.create(
            item_id="7720000000",
            suffix="10",
        ),
        update_type=UpdateType.CREATE,
    )
    db_parent_indent = make_and_get_indent(parent_indent, valid_user, depth=0)

    assert db_parent_indent.nodes.get().get_parent() == root_indent.nodes.get()
    assert db_child1_indent.nodes.get().get_parent() == db_parent_indent.nodes.get()
    assert db_child2_indent.nodes.get().get_parent() == db_parent_indent.nodes.get()
    assert not not_parent.nodes.get().get_descendants().exists()


@pytest.mark.parametrize("item_id,suffix", [("1402000000", "80"), ("1401010000", "20")])
@pytest.mark.parametrize("update_type", [UpdateType.UPDATE, UpdateType.DELETE])
def test_goods_nomenclature_indent_importer_update_with_triple_00_indent(
    valid_user,
    date_ranges,
    item_id,
    suffix,
    update_type,
):
    parent_indent = factories.GoodsNomenclatureIndentFactory.create(
        update_type=UpdateType.CREATE.value,
        indented_goods_nomenclature__item_id="1401000000",
        indented_goods_nomenclature__suffix="20",
        node__parent=factories.GoodsNomenclatureIndentFactory.create(
            indented_goods_nomenclature__item_id="1400000000",
        ).nodes.first(),
    ).nodes.first()

    indent = factories.GoodsNomenclatureIndentFactory.create(
        update_type=UpdateType.CREATE.value,
        indented_goods_nomenclature=factories.SimpleGoodsNomenclatureFactory.create(
            item_id=item_id,
            suffix=suffix,
        ),
        validity_start=date_ranges.normal.lower,
    )

    updated_indent = factories.GoodsNomenclatureIndentFactory.build(
        sid=indent.sid,
        update_type=update_type,
        indented_goods_nomenclature=indent.indented_goods_nomenclature,
        validity_start=date_ranges.adjacent_no_end.lower,
    )

    db_indent = make_and_get_indent(updated_indent, valid_user, depth=0)

    compare_updated_indent(
        updated_indent,
        db_indent,
        indent_level=0,
        count=1,
        depth=3,
        parent_indent=parent_indent,
    )


@pytest.fixture
def make_inappropriate_family(date_ranges, valid_user):
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
    valid_user,
    date_ranges,
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

    new_parent_node = make_and_get_indent(
        factories.GoodsNomenclatureIndentFactory.build(
            indented_goods_nomenclature=factories.GoodsNomenclatureFactory.create(
                item_id="4502000000",
                valid_between=date_ranges.no_end,
            ),
            validity_start=date_ranges.no_end.lower,
            update_type=UpdateType.CREATE,
        ),
        valid_user,
        depth=0,
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
    valid_user,
    date_ranges,
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

    new_parent = make_and_get_indent(
        factories.GoodsNomenclatureIndentFactory.build(
            indented_goods_nomenclature=factories.GoodsNomenclatureFactory.create(
                item_id="4602000000",
                valid_between=date_ranges.adjacent_no_end,
            ),
            validity_start=date_ranges.adjacent_no_end.lower,
            update_type=UpdateType.CREATE,
        ),
        valid_user,
        depth=0,
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
    valid_user,
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

    updated_indent = factories.GoodsNomenclatureIndentFactory.build(
        sid=indent.sid,
        indented_goods_nomenclature=indent.indented_goods_nomenclature,
        validity_start=date_ranges.adjacent_no_end.lower,
        update_type=update_type,
    )

    db_indent = make_and_get_indent(updated_indent, valid_user, depth=0)

    compare_indent(updated_indent, db_indent, indent_level=0, count=1, depth=2)

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


def test_footnote_association_goods_nomenclature_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.FootnoteAssociationGoodsNomenclatureFactory.build(
            goods_nomenclature=factories.GoodsNomenclatureFactory.create(),
            associated_footnote=factories.FootnoteFactory.create(),
        ),
        serializers.FootnoteAssociationGoodsNomenclatureSerializer,
    )


def test_footnote_association_goods_nomenclature_importer_update(
    update_imported_fields_match,
):
    assert update_imported_fields_match(
        factories.FootnoteAssociationGoodsNomenclatureFactory,
        serializers.FootnoteAssociationGoodsNomenclatureSerializer,
        dependencies={
            "goods_nomenclature": factories.GoodsNomenclatureFactory,
            "associated_footnote": factories.FootnoteFactory,
        },
    )
