from datetime import date

import pytest

from additional_codes.new_import_parsers import NewAdditionalCodeDescriptionParser
from importer import new_importer

pytestmark = pytest.mark.django_db


class TestNewAdditionalCodeDescriptionParser:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="additional.code.description" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="additional.code.description.period.sid" type="SID"/>
                    <xs:element name="language.id" type="LanguageId"/>
                    <xs:element name="additional.code.sid" type="SID"/>
                    <xs:element name="additional.code.type.id" type="AdditionalCodeTypeId"/>
                    <xs:element name="additional.code" type="AdditionalCode"/>
                    <xs:element name="description" type="LongDescription" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "additional_code_description_period_sid": "123",
            "additional_code_sid": "123",
            "additional_code_type_id": "123",
            "additional_code": "123",
            "description": "some description",
        }

        target = NewAdditionalCodeDescriptionParser()

        target.populate(
            1,  # transaction id
            target.record_code,
            target.subrecord_code,
            1,  # sequence number
            expected_data_example,
        )

        # verify all properties
        assert target.sid == 123  # converts "additional.code.type.id" to sid
        assert target.described_additionalcode__sid == 123
        assert target.described_additionalcode__type__sid == 123
        assert target.described_additionalcode__code == "123"
        assert target.description == "some description"

    def test_import(self, superuser):
        file_to_import = "./importer_examples/additional_code_description_CREATE.xml"

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
            target_message.record_code == NewAdditionalCodeDescriptionParser.record_code
        )
        assert (
            target_message.subrecord_code
            == NewAdditionalCodeDescriptionParser.subrecord_code
        )
        assert (
            type(
                target_message.taric_object,
            )
            == NewAdditionalCodeDescriptionParser
        )

        # check properties for additional code
        target_taric_object = target_message.taric_object
        assert type(target_taric_object) == NewAdditionalCodeDescriptionParser
        assert target_taric_object.sid == 5
        assert target_taric_object.described_additionalcode__sid == 1
        assert target_taric_object.described_additionalcode__type__sid == 7
        assert target_taric_object.described_additionalcode__code == "2"
        assert target_taric_object.description == "some description"
        assert target_taric_object.validity_start == date(2021, 1, 1)

        for message in importer.parsed_transactions[0].parsed_messages:
            # check for issues
            assert len(message.taric_object.issues) == 0

    def test_import_invalid_additional_code(self, superuser):
        file_to_import = "./importer_examples/additional_code_description_invalid_additional_code_CREATE.xml"
        importer = new_importer.NewImporter(
            file_to_import,
            import_title="Importing stuff",
            author_username=superuser.username,
        )

        # check there is one AdditionalCodeType imported
        assert len(importer.parsed_transactions) == 1
        assert len(importer.parsed_transactions[0].parsed_messages) == 1

        target_message = importer.parsed_transactions[0].parsed_messages[0]

        assert (
            target_message.record_code == NewAdditionalCodeDescriptionParser.record_code
        )
        assert (
            target_message.subrecord_code
            == NewAdditionalCodeDescriptionParser.subrecord_code
        )
        assert type(target_message.taric_object) == NewAdditionalCodeDescriptionParser

        # check properties for additional code
        target_taric_object = target_message.taric_object
        assert target_taric_object.sid == 5
        assert target_taric_object.described_additionalcode__sid == 1
        assert target_taric_object.described_additionalcode__type__sid == 12
        assert target_taric_object.described_additionalcode__code == "111"
        assert target_taric_object.description == "some description"

        assert len(target_taric_object.issues) == 2

        issue_1 = target_taric_object.issues[0]
        issue_2 = target_taric_object.issues[1]

        assert (
            str(issue_1) == "ERROR: No matches for possible related taric object\n"
            "  additional.code.description > additional.code\n"
            "  link_data: {'sid': 1, 'code': '111'}"
        )
        assert (
            str(issue_2) == "ERROR: No matches for possible related taric object\n"
            "  additional.code.description > additional.code.type\n"
            "  link_data: {'sid': 12}"
        )
