from datetime import datetime
from datetime import timezone

import pytest
from psycopg2._range import DateTimeTZRange

from commodities import models
from commodities import serializers
from common.tests import factories
from common.tests.util import generate_test_import_xml
from common.tests.util import requires_update_importer
from common.validators import UpdateType
from importer.management.commands.import_taric import import_taric
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
    assert db_indent.valid_between.lower == indent.valid_between.lower


def compare_updated_indent(
    updated_indent, db_indent, indent_level, count, depth, parent_indent=None
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
        "start_date": "{:%Y-%m-%d}".format(indent.valid_between.lower),
        "indent": depth,
    }

    xml = generate_test_import_xml(data)

    import_taric(xml, valid_user.username, WorkflowStatus.PUBLISHED.value)

    return models.GoodsNomenclatureIndent.objects.filter(
        sid=indent.sid,
    ).last()


def test_goods_nomenclature_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.GoodsNomenclatureFactory, serializers.GoodsNomenclatureSerializer
    )


def test_goods_nomenclature_importer_update(update_imported_fields_match):
    assert update_imported_fields_match(
        factories.GoodsNomenclatureFactory, serializers.GoodsNomenclatureSerializer
    )


def test_goods_nomenclature_description_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.GoodsNomenclatureDescriptionFactory.build(
            described_goods_nomenclature=factories.GoodsNomenclatureFactory.create()
        ),
        serializers.GoodsNomenclatureDescriptionSerializer,
    )


def test_goods_nomenclature_description_importer_update(update_imported_fields_match):
    assert update_imported_fields_match(
        factories.GoodsNomenclatureDescriptionFactory,
        serializers.GoodsNomenclatureDescriptionSerializer,
        dependencies={
            "described_goods_nomenclature": factories.GoodsNomenclatureFactory
        },
    )


def test_goods_nomenclature_origin_importer_create(valid_user, date_ranges):
    origin = factories.GoodsNomenclatureFactory(
        update_type=UpdateType.CREATE.value,
        valid_between=date_ranges.big,
        origin__derived_from_goods_nomenclature__valid_between=date_ranges.adjacent_earlier_big,
    )
    good = factories.GoodsNomenclatureFactory(
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
            origin_link, context={"format": "xml"}
        ).data
    )
    print(xml.read())
    xml.seek(0)

    import_taric(xml, valid_user.username, WorkflowStatus.PUBLISHED.value)

    db_link = models.GoodsNomenclatureOrigin.objects.get(
        new_goods_nomenclature__sid=good.sid
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
            successor_link, context={"format": "xml"}
        ).data
    )

    import_taric(xml, valid_user.username, WorkflowStatus.PUBLISHED.value)

    db_link = models.GoodsNomenclatureSuccessor.objects.get(
        replaced_goods_nomenclature__sid=good.sid
    )
    assert db_link

    db_good = models.GoodsNomenclature.objects.get(sid=good.sid)
    assert db_good.successors.get() == successor


def test_goods_nomenclature_indent_importer_create(valid_user):
    indent = factories.GoodsNomenclatureIndentFactory.build(
        update_type=UpdateType.CREATE.value,
        indented_goods_nomenclature=factories.SimpleGoodsNomenclatureFactory.create(
            item_id="1100000000"
        ),
    )

    db_indent = make_and_get_indent(indent, valid_user, depth=0)

    compare_indent(indent, db_indent, indent_level=0, count=1, depth=1)


@pytest.mark.parametrize("update_type", [UpdateType.UPDATE, UpdateType.DELETE])
def test_goods_nomenclature_indent_importer_update(
    valid_user, date_ranges, update_type
):
    indent = factories.GoodsNomenclatureIndentFactory.create(
        indented_goods_nomenclature=factories.SimpleGoodsNomenclatureFactory.create(
            item_id="2100000000"
        ),
        valid_between=date_ranges.normal,
    )

    updated_indent = factories.GoodsNomenclatureIndentFactory.build(
        sid=indent.sid,
        indented_goods_nomenclature=indent.indented_goods_nomenclature,
        update_type=update_type,
        valid_between=date_ranges.adjacent_no_end,
    )

    db_indent = make_and_get_indent(updated_indent, valid_user, depth=0)

    compare_updated_indent(updated_indent, db_indent, indent_level=0, count=1, depth=1)


def test_goods_nomenclature_indent_importer_create_with_parent_low_indent(valid_user):
    parent_indent = factories.GoodsNomenclatureIndentFactory.create(
        indented_goods_nomenclature__item_id="1200000000"
    ).nodes.first()

    indent = factories.GoodsNomenclatureIndentFactory.build(
        indented_goods_nomenclature=factories.SimpleGoodsNomenclatureFactory.create(
            item_id="1201000000"
        ),
    )

    db_indent = make_and_get_indent(indent, valid_user, depth=0)

    db_indent_node = db_indent.nodes.first()

    compare_indent(indent, db_indent, indent_level=0, count=1, depth=2)
    assert db_indent_node.get_parent() == parent_indent


@pytest.mark.parametrize("update_type", [UpdateType.UPDATE, UpdateType.DELETE])
def test_goods_nomenclature_indent_importer_update_with_parent_low_indent(
    valid_user, date_ranges, update_type
):
    parent_indent = factories.GoodsNomenclatureIndentFactory.create(
        indented_goods_nomenclature__item_id="1200000000"
    ).nodes.first()

    indent = factories.GoodsNomenclatureIndentFactory.create(
        indented_goods_nomenclature=factories.SimpleGoodsNomenclatureFactory.create(
            item_id="1201000000",
        ),
        node__parent=parent_indent,
        valid_between=date_ranges.normal,
    )

    updated_indent = factories.GoodsNomenclatureIndentFactory.build(
        sid=indent.sid,
        indented_goods_nomenclature=indent.indented_goods_nomenclature,
        valid_between=date_ranges.adjacent_no_end,
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
    parent_indent = None
    for idx in range(1, 6):
        parent_indent = factories.GoodsNomenclatureIndentNodeFactory.create(
            indent__indented_goods_nomenclature__item_id=("12" * idx).ljust(10, "0"),
            parent=parent_indent,
        )

    indent = factories.GoodsNomenclatureIndentFactory.build(
        update_type=UpdateType.CREATE.value,
        indented_goods_nomenclature=factories.GoodsNomenclatureFactory.create(
            item_id="1212121215"
        ),
    )

    db_indent = make_and_get_indent(indent, valid_user, depth=4)

    compare_indent(indent, db_indent, 4, 1, 6)


@pytest.mark.parametrize("update_type", [UpdateType.UPDATE, UpdateType.DELETE])
def test_goods_nomenclature_indent_importer_update_with_parent_high_indent(
    valid_user, update_type, date_ranges
):
    parent_indent = None
    for idx in range(1, 6):
        parent_indent = factories.GoodsNomenclatureIndentNodeFactory.create(
            indent__indented_goods_nomenclature__item_id=("12" * idx).ljust(10, "0"),
            parent=parent_indent,
        )

    indent = factories.GoodsNomenclatureIndentFactory.create(
        indented_goods_nomenclature=factories.GoodsNomenclatureFactory.create(
            item_id="1212121215"
        ),
        valid_between=date_ranges.normal,
    )

    updated_indent = factories.GoodsNomenclatureIndentFactory.build(
        sid=indent.sid,
        indented_goods_nomenclature=indent.indented_goods_nomenclature,
        valid_between=date_ranges.adjacent_no_end,
        update_type=update_type,
    )

    db_indent = make_and_get_indent(updated_indent, valid_user, depth=4)

    compare_indent(updated_indent, db_indent, 4, 1, 6)


def test_goods_nomenclature_indent_importer_create_multiple_parents(
    valid_user, date_ranges
):
    """
    In some cases there is an indent which is created which already expects to have multiple parents
    over its lifetime. Assert multiple indent nodes are generated in this scenario.
    """

    indent_validity = DateTimeTZRange(
        date_ranges.adjacent_earlier.lower, date_ranges.adjacent_later.upper
    )
    parent_indent = factories.SimpleGoodsNomenclatureIndentFactory.create(
        valid_between=indent_validity,
        indented_goods_nomenclature__valid_between=indent_validity,
        indented_goods_nomenclature__item_id="1300000000",
    )
    parent_nodes = {
        factories.GoodsNomenclatureIndentNodeFactory.create(
            valid_between=date_ranges.adjacent_earlier,
            indent=parent_indent,
        ),
        factories.GoodsNomenclatureIndentNodeFactory.create(
            valid_between=date_ranges.normal, indent=parent_indent
        ),
        factories.GoodsNomenclatureIndentNodeFactory.create(
            valid_between=date_ranges.adjacent_later, indent=parent_indent
        ),
    }

    indent = factories.GoodsNomenclatureIndentFactory.build(
        update_type=UpdateType.CREATE.value,
        indented_goods_nomenclature=factories.SimpleGoodsNomenclatureFactory.create(
            item_id="1301000000",
            valid_between=indent_validity,
        ),
        valid_between=indent_validity,
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
    assert db_indent.valid_between.lower == indent.valid_between.lower


@pytest.mark.parametrize("update_type", [UpdateType.UPDATE, UpdateType.DELETE])
def test_goods_nomenclature_indent_importer_update_multiple_parents(
    valid_user, date_ranges, update_type
):
    parent_indent = factories.SimpleGoodsNomenclatureIndentFactory.create(
        valid_between=DateTimeTZRange(datetime(2020, 1, 1), datetime(2020, 12, 1)),
        indented_goods_nomenclature__valid_between=DateTimeTZRange(
            datetime(2020, 1, 1), datetime(2020, 12, 1)
        ),
        indented_goods_nomenclature__item_id="1300000000",
    )
    parent1 = factories.GoodsNomenclatureIndentNodeFactory.create(
        valid_between=DateTimeTZRange(datetime(2020, 1, 1), datetime(2020, 4, 1)),
        indent=parent_indent,
    )
    parent2 = factories.GoodsNomenclatureIndentNodeFactory.create(
        valid_between=DateTimeTZRange(datetime(2020, 4, 1), datetime(2020, 8, 1)),
        indent=parent_indent,
    )
    parent3 = factories.GoodsNomenclatureIndentNodeFactory.create(
        valid_between=DateTimeTZRange(datetime(2020, 8, 1), datetime(2020, 12, 1)),
        indent=parent_indent,
    )

    indent = factories.GoodsNomenclatureIndentFactory.build(
        indented_goods_nomenclature=factories.SimpleGoodsNomenclatureFactory.create(
            item_id="1301000000",
            valid_between=DateTimeTZRange(datetime(2020, 1, 1), datetime(2020, 12, 1)),
        ),
        valid_between=DateTimeTZRange(datetime(2020, 1, 1), datetime(2020, 6, 1)),
    )

    first_indent = make_and_get_indent(indent, valid_user, depth=0)
    first_parents = [node.get_parent() for node in first_indent.nodes.all()]

    assert first_parents == [parent1, parent2, parent3]

    updated_indent = factories.GoodsNomenclatureIndentFactory.build(
        sid=first_indent.sid,
        indented_goods_nomenclature=indent.indented_goods_nomenclature,
        valid_between=DateTimeTZRange(
            datetime(2020, 6, 1, tzinfo=timezone.utc), datetime(2020, 12, 1)
        ),
        update_type=update_type,
    )
    second_indent = make_and_get_indent(updated_indent, valid_user, depth=0)
    second_parents = [node.get_parent() for node in second_indent.nodes.all()]

    assert second_indent.sid == first_indent.sid
    assert second_indent.indent == 0
    assert len(second_parents) == 2
    assert second_parents == [parent2, parent3]
    assert (
        second_indent.indented_goods_nomenclature.sid
        == indent.indented_goods_nomenclature.sid
    )
    assert second_indent.valid_between.lower == updated_indent.valid_between.lower


@pytest.mark.parametrize("item_id,suffix", [("1402000000", "80"), ("1401010000", "20")])
def test_goods_nomenclature_indent_importer_create_with_triple_00_indent(
    valid_user, item_id, suffix
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
            indented_goods_nomenclature__item_id="1400000000"
        ).nodes.first(),
    ).nodes.first()

    indent = factories.GoodsNomenclatureIndentFactory.build(
        update_type=UpdateType.CREATE.value,
        indented_goods_nomenclature=factories.SimpleGoodsNomenclatureFactory.create(
            item_id=item_id, suffix=suffix
        ),
    )

    db_indent = make_and_get_indent(indent, valid_user, depth=0)

    compare_indent(indent, db_indent, indent_level=0, count=1, depth=3)


@pytest.mark.parametrize("item_id,suffix", [("1402000000", "80"), ("1401010000", "20")])
@pytest.mark.parametrize("update_type", [UpdateType.UPDATE, UpdateType.DELETE])
def test_goods_nomenclature_indent_importer_update_with_triple_00_indent(
    valid_user, date_ranges, item_id, suffix, update_type
):
    parent_indent = factories.GoodsNomenclatureIndentFactory.create(
        update_type=UpdateType.CREATE.value,
        indented_goods_nomenclature__item_id="1401000000",
        indented_goods_nomenclature__suffix="20",
        node__parent=factories.GoodsNomenclatureIndentFactory.create(
            indented_goods_nomenclature__item_id="1400000000"
        ).nodes.first(),
    ).nodes.first()

    indent = factories.GoodsNomenclatureIndentFactory.create(
        update_type=UpdateType.CREATE.value,
        indented_goods_nomenclature=factories.SimpleGoodsNomenclatureFactory.create(
            item_id=item_id, suffix=suffix
        ),
        valid_between=date_ranges.normal,
    )

    updated_indent = factories.GoodsNomenclatureIndentFactory.build(
        sid=indent.sid,
        update_type=update_type,
        indented_goods_nomenclature=indent.indented_goods_nomenclature,
        valid_between=date_ranges.adjacent_no_end,
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


@requires_update_importer
def test_goods_nomenclature_indent_importer_create_with_branch_shift(valid_user):
    """
    There is an unlikely (query impossible) scenario where a new indent could
    manage to step in between an existing Goods Nomenclature and its parent.

    This would require the tree to be updated once ingested.
    """
    assert False


@requires_update_importer
def test_goods_nomenclature_indent_importer_update_with_branch_shift(valid_user):
    assert False


@pytest.mark.parametrize("update_type", [UpdateType.UPDATE, UpdateType.DELETE])
def test_goods_nomenclature_indent_importer_update_with_children(
    valid_user, update_type, date_ranges
):
    parent_indent = factories.GoodsNomenclatureIndentFactory.create(
        indented_goods_nomenclature__item_id="4400000000",
        valid_between=date_ranges.no_end,
    )

    indent = factories.GoodsNomenclatureIndentFactory.create(
        node__parent=parent_indent.nodes.first(),
        indented_goods_nomenclature__item_id="4401000000",
        valid_between=date_ranges.no_end,
    )

    indent_node = indent.nodes.first()

    child_indent_nodes = {
        factories.GoodsNomenclatureIndentFactory.create(
            indented_goods_nomenclature__item_id=f"44010{idx}0000",
            node__parent=indent_node,
            valid_between=date_ranges.no_end,
        ).nodes.first()
        for idx in range(1, 6)
    }

    updated_indent = factories.GoodsNomenclatureIndentFactory.build(
        sid=indent.sid,
        indented_goods_nomenclature=indent.indented_goods_nomenclature,
        valid_between=date_ranges.adjacent_no_end,
        update_type=update_type,
    )

    db_indent = make_and_get_indent(updated_indent, valid_user, depth=0)

    compare_indent(updated_indent, db_indent, 0, 1, 2)

    db_indent_node = db_indent.nodes.first()
    children = db_indent_node.get_children()
    assert children.count() == 5

    assert any(
        child.valid_between.lower == indent.valid_between.lower
        for child in child_indent_nodes
    )
    assert not any(
        child.valid_between.lower == indent.valid_between.lower for child in children
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
