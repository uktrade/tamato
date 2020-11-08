import pytest
from psycopg2._range import DateTimeTZRange

from commodities import models
from commodities import serializers
from common.tests import factories
from common.tests.util import generate_test_import_xml
from common.tests.util import requires_update_importer
from common.tests.util import validate_taric_import
from common.validators import UpdateType
from importer.management.commands.import_taric import import_taric
from workbaskets.validators import WorkflowStatus


pytestmark = pytest.mark.django_db


def make_and_get_indent(indent, valid_user, depth):
    data = {
        "indented_goods_nomenclature": {
            "sid": indent.indented_goods_nomenclature.sid,
            "item_id": indent.indented_goods_nomenclature.item_id,
            "suffix": indent.indented_goods_nomenclature.suffix,
        },
        "taric_template": "taric/goods_nomenclature_indent.xml",
        "update_type": UpdateType.CREATE.value,
        "sid": indent.sid,
        "start_date": "{:%Y-%m-%d}".format(indent.valid_between.lower),
        "indent": depth,
    }

    xml = generate_test_import_xml(data)
    import_taric(xml, valid_user.username, WorkflowStatus.PUBLISHED.value)

    return models.GoodsNomenclatureIndent.objects.get(
        sid=indent.sid,
    )


@validate_taric_import(
    serializers.GoodsNomenclatureSerializer, factories.GoodsNomenclatureFactory
)
def test_goods_nomenclature_importer_create(valid_user, test_object, db_object):
    assert db_object.item_id == test_object.item_id
    assert db_object.suffix == test_object.suffix
    assert db_object.statistical == test_object.statistical
    assert db_object.valid_between.lower == test_object.valid_between.lower
    assert db_object.valid_between.upper == test_object.valid_between.upper


@validate_taric_import(
    serializers.GoodsNomenclatureDescriptionSerializer,
    factories.GoodsNomenclatureDescriptionFactory,
    dependencies={"described_goods_nomenclature": factories.GoodsNomenclatureFactory},
)
def test_goods_nomenclature_description_importer_create(
    valid_user, test_object, db_object
):
    assert (
        db_object.described_goods_nomenclature
        == test_object.described_goods_nomenclature
    )
    assert db_object.sid == test_object.sid
    assert db_object.description == test_object.description
    assert db_object.valid_between.lower == test_object.valid_between.lower
    assert db_object.valid_between.upper == test_object.valid_between.upper


@requires_update_importer
def test_goods_nomenclature_importer_create_with_origin(valid_user):
    origin = factories.GoodsNomenclatureFactory(update_type=UpdateType.CREATE.value)
    good = factories.GoodsNomenclatureFactory.build(
        update_type=UpdateType.CREATE.value,
        origin__derived_from_goods_nomenclature=origin,
    )

    xml = generate_test_import_xml(
        serializers.GoodsNomenclatureSerializer(good, context={"format": "xml"}).data
    )

    import_taric(xml, valid_user.username, WorkflowStatus.PUBLISHED.value)

    db_good = models.GoodsNomenclature.objects.get(sid=good.sid)

    assert db_good.origins[0] == origin


def test_goods_nomenclature_indent_importer_create(valid_user):
    indent = factories.GoodsNomenclatureIndentFactory.build(
        update_type=UpdateType.CREATE.value,
        indented_goods_nomenclature=factories.SimpleGoodsNomenclatureFactory.create(
            item_id="1100000000"
        ),
    )

    db_indent = make_and_get_indent(indent, valid_user, depth=0)

    assert db_indent.sid == indent.sid
    assert db_indent.indent == 0
    assert db_indent.nodes.count() == 1
    assert db_indent.nodes.first().depth == 1
    assert (
        db_indent.indented_goods_nomenclature.sid
        == indent.indented_goods_nomenclature.sid
    )
    assert db_indent.valid_between.lower == indent.valid_between.lower


def test_goods_nomenclature_indent_importer_create_with_parent_low_indent(valid_user):
    parent_indent = factories.GoodsNomenclatureIndentFactory.create(
        indented_goods_nomenclature__item_id="1200000000"
    ).nodes.first()

    indent = factories.GoodsNomenclatureIndentFactory.build(
        update_type=UpdateType.CREATE.value,
        indented_goods_nomenclature=factories.SimpleGoodsNomenclatureFactory.create(
            item_id="1201000000"
        ),
    )

    db_indent = make_and_get_indent(indent, valid_user, depth=0)

    db_indent_node = db_indent.nodes.first()
    assert db_indent.sid == indent.sid
    assert db_indent.indent == 0
    assert db_indent.nodes.count() == 1
    assert db_indent_node.depth == 2
    assert (
        db_indent.indented_goods_nomenclature.sid
        == indent.indented_goods_nomenclature.sid
    )
    assert db_indent_node.get_parent() == parent_indent
    assert db_indent.valid_between.lower == indent.valid_between.lower


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

    db_indent_node = db_indent.nodes.first()

    assert db_indent.sid == indent.sid
    assert db_indent.indent == 4
    assert db_indent.nodes.count() == 1
    assert db_indent_node.depth == 6
    assert (
        db_indent.indented_goods_nomenclature.sid
        == indent.indented_goods_nomenclature.sid
    )
    assert db_indent_node.get_parent() == parent_indent
    assert db_indent.valid_between.lower == indent.valid_between.lower


def test_goods_nomenclature_indent_importer_multiple_parents(valid_user, date_ranges):
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
    parent_indent = factories.GoodsNomenclatureIndentFactory.create(
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

    db_indent_node = db_indent.nodes.first()
    assert db_indent.sid == indent.sid
    assert db_indent.indent == 0
    assert db_indent.nodes.count() == 1
    assert db_indent_node.depth == 3
    assert (
        db_indent.indented_goods_nomenclature.sid
        == indent.indented_goods_nomenclature.sid
    )
    assert db_indent_node.get_parent() == parent_indent
    assert db_indent.valid_between.lower == indent.valid_between.lower


@requires_update_importer
def test_goods_nomenclature_indent_importer_create_with_branch_shift(valid_user):
    """
    There is an unlikely (query impossible) scenario where a new indent could
    manage to step in between an existing Goods Nomenclature and its parent.

    This would require the tree to be updated once ingested.
    """
    assert False


@validate_taric_import(
    serializers.FootnoteAssociationGoodsNomenclatureSerializer,
    factories.FootnoteAssociationGoodsNomenclatureFactory,
    dependencies={
        "goods_nomenclature": factories.GoodsNomenclatureFactory,
        "associated_footnote": factories.FootnoteFactory,
    },
)
def test_footnote_association_goods_nomenclature_importer_create(
    valid_user, test_object, db_object
):
    assert test_object.valid_between.lower == db_object.valid_between.lower
    assert test_object.valid_between.upper == db_object.valid_between.upper
    assert test_object.goods_nomenclature == db_object.goods_nomenclature
    assert test_object.associated_footnote == db_object.associated_footnote
