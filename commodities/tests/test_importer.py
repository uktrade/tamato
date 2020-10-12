import pytest

from commodities import models
from commodities import serializers
from commodities.import_handlers import InvalidIndentError
from common.tests import factories
from common.tests.util import generate_test_import_xml
from common.tests.util import requires_update_importer
from common.tests.util import validate_taric_import
from common.validators import UpdateType
from importer.management.commands.import_taric import import_taric
from workbaskets.validators import WorkflowStatus


pytestmark = pytest.mark.django_db


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
        update_type=UpdateType.CREATE.value, origin=origin
    )

    xml = generate_test_import_xml(
        serializers.GoodsNomenclatureSerializer(good, context={"format": "xml"}).data
    )

    import_taric(xml, valid_user.username, WorkflowStatus.PUBLISHED.value)

    db_good = models.GoodsNomenclature.objects.get(sid=good.sid)

    assert db_good.origin == origin


def test_goods_nomenclature_indent_importer_create(valid_user):
    test_object = factories.GoodsNomenclatureIndentFactory.build(
        update_type=UpdateType.CREATE.value,
        indented_goods_nomenclature=factories.GoodsNomenclatureFactory.create(
            item_id="1100000000"
        ),
    )

    @validate_taric_import(
        serializers.GoodsNomenclatureIndentSerializer, instance=test_object
    )
    def assert_func(valid_user, test_object, db_object):
        assert db_object.sid == test_object.sid
        assert db_object.depth == test_object.depth
        assert (
            db_object.indented_goods_nomenclature.sid
            == test_object.indented_goods_nomenclature.sid
        )
        assert db_object.valid_between.lower == test_object.valid_between.lower

    assert_func(valid_user)


def test_goods_nomenclature_indent_importer_create_with_parent_low_indent(valid_user):
    parent_indent = factories.GoodsNomenclatureIndentFactory.create(
        indented_goods_nomenclature__item_id="1200000000"
    )

    test_object = factories.GoodsNomenclatureIndentFactory.build(
        update_type=UpdateType.CREATE.value,
        indented_goods_nomenclature=factories.SimpleGoodsNomenclatureFactory.create(
            item_id="1201000000"
        ),
        parent=parent_indent,
    )

    @validate_taric_import(
        serializers.GoodsNomenclatureIndentSerializer, instance=test_object
    )
    def assert_func(valid_user, test_object, db_object):
        assert db_object.sid == test_object.sid
        assert db_object.depth == test_object.depth
        assert db_object.depth == 2
        assert (
            db_object.indented_goods_nomenclature.sid
            == test_object.indented_goods_nomenclature.sid
        )
        assert db_object.get_parent() == parent_indent
        assert db_object.valid_between.lower == test_object.valid_between.lower

    assert_func(valid_user)


def test_goods_nomenclature_indent_importer_create_with_parent_high_indent(valid_user):
    parent_indent = None
    for idx in range(1, 6):
        parent_indent = factories.GoodsNomenclatureIndentFactory.create(
            indented_goods_nomenclature__item_id=("12" * idx).ljust(10, "0"),
            parent=parent_indent,
        )

    test_object = factories.GoodsNomenclatureIndentFactory.build(
        update_type=UpdateType.CREATE.value,
        indented_goods_nomenclature=factories.GoodsNomenclatureFactory.create(
            item_id="1212121215"
        ),
        parent=parent_indent,
    )

    @validate_taric_import(
        serializers.GoodsNomenclatureIndentSerializer, instance=test_object
    )
    def assert_func(valid_user, test_object, db_object):
        assert db_object.sid == test_object.sid
        assert db_object.depth == test_object.depth
        assert db_object.depth == 6
        assert (
            db_object.indented_goods_nomenclature.sid
            == test_object.indented_goods_nomenclature.sid
        )
        assert db_object.get_parent() == parent_indent
        assert db_object.valid_between.lower == test_object.valid_between.lower

    assert_func(valid_user)


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
