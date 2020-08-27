import pytest

from commodities import models
from commodities import serializers
from common.tests import factories
from common.tests.factories import FootnoteAssociationGoodsNomenclatureFactory
from common.tests.util import generate_test_import_xml
from common.tests.util import requires_interdependent_export
from common.validators import UpdateType
from importer.management.commands.import_taric import import_taric
from workbaskets.validators import WorkflowStatus

pytestmark = pytest.mark.django_db


def test_goods_nomenclature_importer_create(valid_user):
    good = factories.GoodsNomenclatureFactory.build(update_type=UpdateType.CREATE.value)
    xml = generate_test_import_xml(
        serializers.GoodsNomenclatureSerializer(good, context={"format": "xml"}).data
    )

    import_taric(xml, valid_user.username, WorkflowStatus.PUBLISHED.value)

    db_good = models.GoodsNomenclature.objects.get(sid=good.sid)

    assert db_good.item_id == good.item_id
    assert db_good.suffix == good.suffix
    assert db_good.statistical == good.statistical
    assert db_good.valid_between.lower == good.valid_between.lower
    assert db_good.valid_between.upper == good.valid_between.upper


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


def test_footnote_association_goods_nomenclature_importer_create(valid_user):
    good = factories.GoodsNomenclatureFactory()
    footnote = factories.FootnoteFactory()

    association = FootnoteAssociationGoodsNomenclatureFactory.build(
        update_type=UpdateType.CREATE.value,
        goods_nomenclature=good,
        associated_footnote=footnote,
    )

    xml = generate_test_import_xml(
        serializers.FootnoteAssociationGoodsNomenclatureSerializer(
            association, context={"format": "xml"}
        ).data
    )

    import_taric(xml, valid_user.username, WorkflowStatus.PUBLISHED.value)

    db_association = models.FootnoteAssociationGoodsNomenclature.objects.get(
        goods_nomenclature=good,
        associated_footnote=footnote,
    )

    assert db_association.valid_between.lower == association.valid_between.lower
    assert db_association.valid_between.upper == association.valid_between.upper
    assert db_association.goods_nomenclature == good
    assert db_association.associated_footnote == footnote
