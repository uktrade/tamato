import pytest

# note : need to import these objects to make them available to the parser
from commodities.models import GoodsNomenclatureSuccessor
from commodities.new_import_parsers import NewGoodsNomenclatureSuccessorParser
from common.tests.util import preload_import

pytestmark = pytest.mark.django_db


@pytest.mark.new_importer
class TestNewGoodsNomenclatureSuccessorParser:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="goods.nomenclature.successor" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="goods.nomenclature.sid" type="SID"/>
                    <xs:element name="absorbed.goods.nomenclature.item.id" type="GoodsNomenclatureItemId"/>
                    <xs:element name="absorbed.productline.suffix" type="ProductLineSuffix"/>
                    <xs:element name="goods.nomenclature.item.id" type="GoodsNomenclatureItemId"/>
                    <xs:element name="productline.suffix" type="ProductLineSuffix"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    target_parser_class = NewGoodsNomenclatureSuccessorParser

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "goods_nomenclature_sid": "555",
            "goods_nomenclature_item_id": "0100000000",
            "absorbed_goods_nomenclature_item_id": "0101000000",
            "absorbed_productline_suffix": "10",
            "productline_suffix": "10",
        }

        target = self.target_parser_class()

        target.populate(
            1,  # transaction id
            target.record_code,
            target.subrecord_code,
            1,  # sequence number
            expected_data_example,
        )

        # verify all properties
        assert target.replaced_goods_nomenclature__sid == 555
        assert target.replaced_goods_nomenclature__item_id == "0100000000"
        assert target.replaced_goods_nomenclature__suffix == 10
        assert target.absorbed_into_goods_nomenclature__item_id == "0101000000"
        assert target.absorbed_into_goods_nomenclature__suffix == 10

    def test_import(self, superuser):
        importer = preload_import("goods_nomenclature_successor_CREATE.xml", __file__)

        assert len(importer.parsed_transactions) == 1
        assert len(importer.parsed_transactions[0].parsed_messages) == 4

        target_message = importer.parsed_transactions[0].parsed_messages[3]

        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target = target_message.taric_object

        assert target.absorbed_into_goods_nomenclature__item_id == "0102000000"
        assert target.absorbed_into_goods_nomenclature__suffix == 10
        assert target.replaced_goods_nomenclature__sid == 2
        assert target.replaced_goods_nomenclature__item_id == "0101000000"
        assert target.replaced_goods_nomenclature__suffix == 10

        assert GoodsNomenclatureSuccessor.objects.all().count() == 1

        assert len(importer.issues()) == 0

    def test_import_update_raises_issue(self, superuser):
        preload_import("goods_nomenclature_successor_CREATE.xml", __file__, True)
        importer = preload_import("goods_nomenclature_successor_UPDATE.xml", __file__)

        assert len(importer.issues()) == 1

        assert (
            "Taric objects of type GoodsNomenclatureSuccessor can't be updated"
            in str(importer.issues()[0])
        )

    def test_import_delete_raises_issue(self, superuser):
        preload_import("goods_nomenclature_successor_CREATE.xml", __file__, True)
        importer = preload_import("goods_nomenclature_successor_DELETE.xml", __file__)

        assert len(importer.issues()) == 0
        assert importer.can_save()
