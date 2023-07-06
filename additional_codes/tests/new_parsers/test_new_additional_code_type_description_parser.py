import pytest

from additional_codes.new_import_parsers import NewAdditionalCodeTypeDescriptionParser
from importer import new_importer

pytestmark = pytest.mark.django_db


class TestNewAdditionalCodeTypeDescriptionParser:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="additional.code.type.description" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="additional.code.type.id" type="AdditionalCodeTypeId"/>
                    <xs:element name="language.id" type="LanguageId"/>
                    <xs:element name="description" type="ShortDescription" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "additional_code_type_id": "123",
            "description": "some description",
        }

        target = NewAdditionalCodeTypeDescriptionParser()

        target.populate(
            1,  # transaction id
            target.record_code,
            target.subrecord_code,
            1,  # sequence number
            expected_data_example,
        )

        # verify all properties
        assert target.sid == 123  # converts "additional.code.type.id" to sid
        assert target.description == "some description"

    def test_import(self, superuser):
        file_to_import = (
            "./importer_examples/additional_code_type_description_CREATE.xml"
        )

        importer = new_importer.NewImporter(
            file_to_import,
            "Importing stuff",
            superuser.username,
        )

        # check there is one AdditionalCodeType imported
        assert len(importer.parsed_transactions) == 1
        assert len(importer.parsed_transactions[0].parsed_messages) == 2

        target_message = importer.parsed_transactions[0].parsed_messages[1]
        assert (
            target_message.record_code
            == NewAdditionalCodeTypeDescriptionParser.record_code
        )
        assert (
            target_message.subrecord_code
            == NewAdditionalCodeTypeDescriptionParser.subrecord_code
        )
        assert (
            type(
                target_message.taric_object,
            )
            == NewAdditionalCodeTypeDescriptionParser
        )

        # check properties for additional code
        target_taric_object = target_message.taric_object
        assert target_taric_object.sid == 12
        assert target_taric_object.description == "some description"

        # check for issues
        for message in importer.parsed_transactions[0].parsed_messages:
            assert len(message.taric_object.issues) == 0

    def test_import_invalid_type(self, superuser):
        file_to_import = "./importer_examples/additional_code_type_description_without_type_CREATE.xml"

        importer = new_importer.NewImporter(
            file_to_import,
            "Importing stuff",
            superuser.username,
        )

        # check there is one AdditionalCodeType imported
        assert len(importer.parsed_transactions) == 1
        assert len(importer.parsed_transactions[0].parsed_messages) == 1

        target_message = importer.parsed_transactions[0].parsed_messages[0]
        assert (
            target_message.record_code
            == NewAdditionalCodeTypeDescriptionParser.record_code
        )
        assert (
            target_message.subrecord_code
            == NewAdditionalCodeTypeDescriptionParser.subrecord_code
        )
        assert (
            type(target_message.taric_object) == NewAdditionalCodeTypeDescriptionParser
        )

        # check properties for additional code
        target_taric_object = target_message.taric_object
        assert target_taric_object.sid == 12
        assert target_taric_object.description == "some description"

        assert len(target_taric_object.issues) == 1
        assert (
            str(target_taric_object.issues[0])
            == "ERROR: No matches for possible related taric object\n"
            "  additional.code.type.description > additional.code.type\n"
            "  link_data: {'sid': 12}"
        )
