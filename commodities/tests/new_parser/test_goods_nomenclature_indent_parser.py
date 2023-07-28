import os
from datetime import date

import pytest

# note : need to import these objects to make them available to the parser
from commodities.models import GoodsNomenclatureIndent
from commodities.new_import_parsers import NewGoodsNomenclatureIndentParser
from importer import new_importer

pytestmark = pytest.mark.django_db


def get_test_xml_file(file_name):
    path_to_current_file = os.path.realpath(__file__)
    current_directory = os.path.split(path_to_current_file)[0]
    return os.path.join(current_directory, "importer_examples", file_name)


class TestNewGoodsNomenclatureIndentParser:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="goods.nomenclature.indents" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="goods.nomenclature.indent.sid" type="SID"/>
                    <xs:element name="goods.nomenclature.sid" type="SID"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="number.indents" type="NumberOf"/>
                    <xs:element name="goods.nomenclature.item.id" type="GoodsNomenclatureItemId"/>
                    <xs:element name="productline.suffix" type="ProductLineSuffix"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "goods_nomenclature_indent_sid": "8",
            "goods_nomenclature_sid": "555",
            "goods_nomenclature_item_id": "0100000000",
            "productline_suffix": "10",
            "validity_start_date": "2022-01-01",
            "number_indents": "2",
        }

        target = NewGoodsNomenclatureIndentParser()

        target.populate(
            1,  # transaction id
            target.record_code,
            target.subrecord_code,
            1,  # sequence number
            expected_data_example,
        )

        # verify all properties
        assert target.sid == 8  # converts "certificate_code" to sid
        assert target.indented_goods_nomenclature__sid == 555
        assert target.validity_start == date(2022, 1, 1)
        assert target.indent == 2  # converts "certificate_code" to sid
        assert target.indented_goods_nomenclature__item_id == "0100000000"
        assert target.indented_goods_nomenclature__suffix == 10

    def test_import(self, superuser):
        file_to_import = get_test_xml_file("goods_nomenclature_indent_CREATE.xml")

        importer = new_importer.NewImporter(
            file_to_import,
            import_title="Importing stuff",
            author_username=superuser.username,
        )

        # check there is one AdditionalCodeType imported
        assert len(importer.parsed_transactions) == 2
        assert len(importer.parsed_transactions[0].parsed_messages) == 1
        assert len(importer.parsed_transactions[1].parsed_messages) == 1

        target_message = importer.parsed_transactions[1].parsed_messages[0]

        assert (
            target_message.record_code == NewGoodsNomenclatureIndentParser.record_code
        )
        assert (
            target_message.subrecord_code
            == NewGoodsNomenclatureIndentParser.subrecord_code
        )
        assert type(target_message.taric_object) == NewGoodsNomenclatureIndentParser

        # check properties for additional code
        target = target_message.taric_object

        assert target.sid == 9  # converts "certificate_code" to sid
        assert target.indented_goods_nomenclature__sid == 1
        assert target.validity_start == date(2021, 1, 1)
        assert target.indent == 1
        assert (
            target.indented_goods_nomenclature__item_id == "0100000000"
        )  # converts "certificate_code" to sid
        assert (
            target.indented_goods_nomenclature__suffix == 10
        )  # converts "certificate_code" to sid

        assert GoodsNomenclatureIndent.objects.all().count() == 1

        assert len(importer.issues()) == 0
