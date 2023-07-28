import os
from datetime import date

import pytest

# note : need to import these objects to make them available to the parser
from commodities.models import GoodsNomenclature
from commodities.new_import_parsers import NewGoodsNomenclatureParser
from importer import new_importer

pytestmark = pytest.mark.django_db


def get_test_xml_file(file_name):
    path_to_current_file = os.path.realpath(__file__)
    current_directory = os.path.split(path_to_current_file)[0]
    return os.path.join(current_directory, "importer_examples", file_name)


class TestNewGoodsNomenclatureParser:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="goods.nomenclature" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="goods.nomenclature.sid" type="SID"/>
                    <xs:element name="goods.nomenclature.item.id" type="GoodsNomenclatureItemId"/>
                    <xs:element name="producline.suffix" type="ProductLineSuffix"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                    <xs:element name="statistical.indicator" type="StatisticalIndicator"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "goods_nomenclature_sid": "555",
            "goods_nomenclature_item_id": "0100000000",  # gets ignored, but will come in from import
            "productline_suffix": "10",
            "validity_start_date": "2020-01-01",
            "validity_end_date": "2020-12-01",
            "statistical_indicator": "0",
        }

        target = NewGoodsNomenclatureParser()

        target.populate(
            1,  # transaction id
            target.record_code,
            target.subrecord_code,
            1,  # sequence number
            expected_data_example,
        )

        # verify all properties
        assert target.sid == 555  # converts "certificate_code" to sid
        assert target.item_id == "0100000000"  # converts "certificate_code" to sid
        assert target.suffix == 10
        assert target.valid_between_lower == date(2020, 1, 1)
        assert target.valid_between_upper == date(2020, 12, 1)
        assert target.statistical == 0

    def test_import(self, superuser):
        file_to_import = get_test_xml_file("goods_nomenclature_CREATE.xml")

        importer = new_importer.NewImporter(
            file_to_import,
            import_title="Importing stuff",
            author_username=superuser.username,
        )

        # check there is one AdditionalCodeType imported
        assert len(importer.parsed_transactions) == 1
        assert len(importer.parsed_transactions[0].parsed_messages) == 1

        target_message = importer.parsed_transactions[0].parsed_messages[0]

        assert target_message.record_code == NewGoodsNomenclatureParser.record_code
        assert (
            target_message.subrecord_code == NewGoodsNomenclatureParser.subrecord_code
        )
        assert type(target_message.taric_object) == NewGoodsNomenclatureParser

        # check properties for additional code
        target_taric_object = target_message.taric_object
        assert target_taric_object.sid == 1
        assert (
            target_taric_object.item_id == "0100000000"
        )  # converts "certificate_code" to sid
        assert target_taric_object.suffix == 10
        assert target_taric_object.valid_between_lower == date(2021, 1, 1)
        assert target_taric_object.valid_between_upper is None
        assert target_taric_object.statistical == 0

        assert GoodsNomenclature.objects.all().count() == 1

        for message in importer.parsed_transactions[0].parsed_messages:
            # check for issues
            errors = ""
            for issue in message.taric_object.issues:
                errors += f"{issue}"
            assert len(message.taric_object.issues) == 0, errors
