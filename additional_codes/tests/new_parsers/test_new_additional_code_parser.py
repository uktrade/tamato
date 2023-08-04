from datetime import date

import pytest

from additional_codes.new_import_parsers import NewAdditionalCodeParser
from additional_codes.new_import_parsers import NewAdditionalCodeTypeParser
from common.tests.util import get_test_xml_file
from importer import new_importer

pytestmark = pytest.mark.django_db


@pytest.mark.new_importer
class TestNewAdditionalCodeParser:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="additional.code" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="additional.code.sid" type="SID"/>
                    <xs:element name="additional.code.type.id" type="AdditionalCodeTypeId"/>
                    <xs:element name="additional.code" type="AdditionalCode"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    target_parser_class = NewAdditionalCodeParser

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "additional_code_sid": 123,
            "additional_code_type_id": 123,
            "additional_code": "123",
            "validity_start_date": "2023-01-22",
            "validity_end_date": "2024-01-22",
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
        assert target.sid == 123  # converts "additional.code.sid" to sid
        assert target.type__sid == 123
        assert target.code == "123"  # converts "additional.code" to code
        assert target.valid_between_lower == date(2023, 1, 22)
        assert target.valid_between_upper == date(2024, 1, 22)

    def test_import_success(self, superuser):
        file_to_import = get_test_xml_file("additional_code_CREATE.xml", __file__)

        importer = new_importer.NewImporter(
            file_to_import,
            "Importing stuff",
            superuser.username,
        )

        # check there is one AdditionalCodeType imported
        assert len(importer.parsed_transactions) == 1
        assert len(importer.parsed_transactions[0].parsed_messages) == 3

        # adding additional code
        target_message = importer.parsed_transactions[0].parsed_messages[1]
        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        # check properties for additional code
        taric_object = target_message.taric_object
        assert taric_object.sid == 1
        assert taric_object.valid_between_lower == date(2021, 1, 1)
        assert taric_object.valid_between_upper is None
        assert taric_object.type__sid == 5
        assert taric_object.code == "3"

        # check for issues
        assert len(importer.issues()) == 0

    def test_import_invalid_type(self, superuser):
        file_to_import = get_test_xml_file(
            "additional_code_invalid_type_CREATE.xml",
            __file__,
        )

        importer = new_importer.NewImporter(
            file_to_import,
            "Importing stuff",
            superuser.username,
        )

        # check there is one AdditionalCodeType imported
        assert len(importer.parsed_transactions) == 1
        assert len(importer.parsed_transactions[0].parsed_messages) == 1
        # adding additional code
        assert (
            importer.parsed_transactions[0].parsed_messages[0].record_code
            == NewAdditionalCodeParser.record_code
        )
        assert (
            importer.parsed_transactions[0].parsed_messages[0].subrecord_code
            == NewAdditionalCodeTypeParser.subrecord_code
        )
        assert (
            type(importer.parsed_transactions[0].parsed_messages[0].taric_object)
            == NewAdditionalCodeParser
        )

        # check properties for additional code
        taric_object = importer.parsed_transactions[0].parsed_messages[0].taric_object
        assert taric_object.sid == 1
        assert taric_object.valid_between_lower == date(2021, 1, 1)
        assert taric_object.valid_between_upper is None
        assert taric_object.type__sid == 12
        assert taric_object.code == "111"

        # check for issues
        assert len(importer.issues()) == 2
