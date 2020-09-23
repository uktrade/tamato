import pytest

from common.tests import factories
from common.tests.util import validate_taric_xml

pytestmark = pytest.mark.django_db


@validate_taric_xml(factories.GoodsNomenclatureFactory)
def test_goods_nomenclature_xml(api_client, taric_schema, approved_workbasket, xml):
    element = xml.find(".//goods.nomenclature", xml.nsmap)
    assert element is not None


@validate_taric_xml(factories.GoodsNomenclatureIndentFactory)
def test_goods_nomenclature_indent_xml(
    api_client, taric_schema, approved_workbasket, xml
):
    element = xml.find(".//goods.nomenclature.indents", xml.nsmap)
    assert element is not None


def goods_nomenclature_relation_test(
    relation_name, api_client, taric_schema, approved_workbasket, date_ranges
):
    parent = factories.GoodsNomenclatureIndentFactory(
        valid_between=date_ranges.big, workbasket=approved_workbasket
    )
    origin = factories.GoodsNomenclatureFactory(
        workbasket=approved_workbasket,
        valid_between=date_ranges.normal,
        indent__parent=parent,
    )

    @validate_taric_xml(
        factories.GoodsNomenclatureFactory,
        factory_kwargs={
            "indent__parent": parent,
            "origin": origin,
            "valid_between": date_ranges.adjacent_later,
        },
    )
    def run_test(*_args, xml=None):
        element = xml.find(relation_name, xml.nsmap)
        assert element is not None

    run_test(api_client, taric_schema, approved_workbasket)


def test_goods_nomenclature_origin_xml(
    api_client, taric_schema, approved_workbasket, date_ranges
):
    goods_nomenclature_relation_test(
        ".//goods.nomenclature.origin",
        api_client,
        taric_schema,
        approved_workbasket,
        date_ranges,
    )


def test_goods_nomenclature_successor_xml(
    api_client, taric_schema, approved_workbasket, date_ranges
):
    goods_nomenclature_relation_test(
        ".//goods.nomenclature.successor",
        api_client,
        taric_schema,
        approved_workbasket,
        date_ranges,
    )


@validate_taric_xml(factories.GoodsNomenclatureDescriptionFactory)
def test_goods_nomenclature_description_xml(
    api_client, taric_schema, approved_workbasket, xml
):
    element = xml.find(".//goods.nomenclature.description", xml.nsmap)
    assert element is not None
    element = xml.find(".//goods.nomenclature.description.period", xml.nsmap)
    assert element is not None


@validate_taric_xml(factories.FootnoteAssociationGoodsNomenclatureFactory)
def test_footnote_association_goods_nomenclature_xml(
    api_client, taric_schema, approved_workbasket, xml
):
    element = xml.find(".//footnote.association.goods.nomenclature", xml.nsmap)
    assert element is not None
