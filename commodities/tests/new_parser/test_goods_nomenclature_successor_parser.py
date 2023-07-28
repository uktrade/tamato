import os

import pytest

# note : need to import these objects to make them available to the parser
from commodities.models import GoodsNomenclatureSuccessor
from commodities.new_import_parsers import NewGoodsNomenclatureSuccessorParser
from importer import new_importer

pytestmark = pytest.mark.django_db


def get_test_xml_file(file_name):
    path_to_current_file = os.path.realpath(__file__)
    current_directory = os.path.split(path_to_current_file)[0]
    return os.path.join(current_directory, "importer_examples", file_name)


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

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "goods_nomenclature_sid": "555",
            "goods_nomenclature_item_id": "0100000000",
            "absorbed_goods_nomenclature_item_id": "0101000000",
            "absorbed_productline_suffix": "10",
            "productline_suffix": "10",
        }

        target = NewGoodsNomenclatureSuccessorParser()

        target.populate(
            1,  # transaction id
            target.record_code,
            target.subrecord_code,
            1,  # sequence number
            expected_data_example,
        )

        # verify all properties
        assert (
            target.replaced_goods_nomenclature__sid == 555
        )  # converts "certificate_code" to sid
        assert target.replaced_goods_nomenclature__item_id == "0100000000"
        assert target.replaced_goods_nomenclature__suffix == 10
        assert (
            target.absorbed_into_goods_nomenclature__item_id == "0101000000"
        )  # converts "certificate_code" to sid
        assert target.absorbed_into_goods_nomenclature__suffix == 10

    def test_import(self, superuser):
        file_to_import = get_test_xml_file("goods_nomenclature_successor_CREATE.xml")

        importer = new_importer.NewImporter(
            file_to_import,
            import_title="Importing stuff",
            author_username=superuser.username,
        )

        # check there is one AdditionalCodeType imported
        assert len(importer.parsed_transactions) == 1
        assert len(importer.parsed_transactions[0].parsed_messages) == 4

        target_message = importer.parsed_transactions[0].parsed_messages[3]

        assert (
            target_message.record_code
            == NewGoodsNomenclatureSuccessorParser.record_code
        )
        assert (
            target_message.subrecord_code
            == NewGoodsNomenclatureSuccessorParser.subrecord_code
        )
        assert type(target_message.taric_object) == NewGoodsNomenclatureSuccessorParser

        # check properties for additional code
        target = target_message.taric_object

        assert (
            target.absorbed_into_goods_nomenclature__item_id == "0102000000"
        )  # converts "certificate_code" to sid
        assert target.absorbed_into_goods_nomenclature__suffix == 10
        assert target.replaced_goods_nomenclature__sid == 2
        assert target.replaced_goods_nomenclature__item_id == "0101000000"
        assert (
            target.replaced_goods_nomenclature__suffix == 10
        )  # converts "certificate_code" to sid

        assert GoodsNomenclatureSuccessor.objects.all().count() == 1

        for message in importer.parsed_transactions[0].parsed_messages:
            # check for issues
            errors = ""
            for issue in message.taric_object.issues:
                errors += f"{issue}"
            assert len(message.taric_object.issues) == 0, errors
