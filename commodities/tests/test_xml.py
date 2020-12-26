import pytest

from common.tests import factories
from common.tests.util import validate_taric_xml

pytestmark = pytest.mark.django_db


@validate_taric_xml(factories.GoodsNomenclatureFactory)
def test_goods_nomenclature_xml(api_client, taric_schema, approved_transaction, xml):
    element = xml.find(".//goods.nomenclature", xml.nsmap)
    assert element is not None


@validate_taric_xml(factories.GoodsNomenclatureIndentFactory)
def test_goods_nomenclature_indent_xml(
    api_client, taric_schema, approved_transaction, xml
):
    element = xml.find(".//goods.nomenclature.indents", xml.nsmap)
    assert element is not None


@validate_taric_xml(factories.GoodsNomenclatureOriginFactory)
def test_goods_nomenclature_origin_xml(
    api_client, taric_schema, approved_transaction, xml
):
    element = xml.find(".//goods.nomenclature.origin", xml.nsmap)
    assert element is not None


@validate_taric_xml(factories.GoodsNomenclatureSuccessorFactory)
def test_goods_nomenclature_successor_xml(
    api_client, taric_schema, approved_transaction, xml
):
    element = xml.find(".//goods.nomenclature.successor", xml.nsmap)
    assert element is not None


@validate_taric_xml(factories.GoodsNomenclatureDescriptionFactory)
def test_goods_nomenclature_description_xml(
    api_client, taric_schema, approved_transaction, xml
):
    element = xml.find(".//goods.nomenclature.description", xml.nsmap)
    assert element is not None
    element = xml.find(".//goods.nomenclature.description.period", xml.nsmap)
    assert element is not None


@validate_taric_xml(factories.FootnoteAssociationGoodsNomenclatureFactory)
def test_footnote_association_goods_nomenclature_xml(
    api_client, taric_schema, approved_transaction, xml
):
    element = xml.find(".//footnote.association.goods.nomenclature", xml.nsmap)
    assert element is not None
