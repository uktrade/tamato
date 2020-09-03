import pytest

from commodities import models
from commodities import serializers
from common.tests import factories
from common.tests.util import generate_test_import_xml
from common.tests.util import requires_interdependent_export
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


@requires_interdependent_export
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


@pytest.mark.skip(
    "Requires specific commodity code hierarchical importer implementation."
)
def test_goods_nomenclature_indent_importer_create(valid_user):
    good = factories.GoodsNomenclatureFactory()
    indent = factories.GoodsNomenclatureIndentFactory.build(
        update_type=UpdateType.CREATE.value, indented_goods_nomenclature=good
    )
    xml = generate_test_import_xml(
        serializers.GoodsNomenclatureIndentSerializer(
            indent, context={"format": "xml"}
        ).data
    )

    import_taric(xml, valid_user.username, WorkflowStatus.PUBLISHED.value)

    db_indent = models.GoodsNomenclatureIndent.objects.get(sid=indent.sid)

    assert db_indent.sid == indent.sid
    assert db_indent.depth == indent.depth
    assert (
        db_indent.indented_goods_nomenclature.sid
        == indent.indented_goods_nomenclature.sid
    )
    assert db_indent.valid_between.lower == indent.valid_between.lower


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
