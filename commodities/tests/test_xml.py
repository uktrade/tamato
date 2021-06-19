import pytest

from common.tests import factories
from common.tests.util import validate_taric_xml
from common.xml.namespaces import nsmap

pytestmark = pytest.mark.django_db


@validate_taric_xml(factories.SimpleGoodsNomenclatureFactory)
def test_goods_nomenclature_xml(xml):
    element = xml.find(".//oub:goods.nomenclature", nsmap)
    assert element is not None


@validate_taric_xml(factories.GoodsNomenclatureIndentFactory)
def test_goods_nomenclature_indent_xml(xml):
    element = xml.find(".//oub:goods.nomenclature.indents", nsmap)
    assert element is not None


@validate_taric_xml(factories.GoodsNomenclatureOriginFactory)
def test_goods_nomenclature_origin_xml(xml):
    element = xml.find(".//oub:goods.nomenclature.origin", nsmap)
    assert element is not None


@validate_taric_xml(factories.GoodsNomenclatureSuccessorFactory)
def test_goods_nomenclature_successor_xml(xml):
    element = xml.find(".//oub:goods.nomenclature.successor", nsmap)
    assert element is not None


@validate_taric_xml(factories.GoodsNomenclatureDescriptionFactory)
def test_goods_nomenclature_description_xml(xml):
    element = xml.find(".//oub:goods.nomenclature.description", nsmap)
    assert element is not None
    element = xml.find(".//oub:goods.nomenclature.description.period", nsmap)
    assert element is not None


@validate_taric_xml(factories.FootnoteAssociationGoodsNomenclatureFactory)
def test_footnote_association_goods_nomenclature_xml(xml):
    element = xml.find(".//oub:footnote.association.goods.nomenclature", nsmap)
    assert element is not None
