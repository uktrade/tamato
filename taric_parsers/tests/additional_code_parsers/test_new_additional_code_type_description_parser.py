import pytest

from common.tests.util import preload_import
from taric_parsers.parsers.additional_code_parsers import *

pytestmark = pytest.mark.django_db


@pytest.mark.new_importer
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

    target_parser_class = NewAdditionalCodeTypeDescriptionParser

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "additional_code_type_id": "B",
            "description": "some description",
        }

        target = self.target_parser_class()

        target.populate(
            1,  # transaction id
            target.record_code,
            target.subrecord_code,
            1,  # sequence number
            expected_data_example,
        )

        assert target.sid == "B"
        assert target.description == "some description"

    def test_import(self, superuser):
        importer = preload_import(
            "additional_code_type_description_CREATE.xml",
            __file__,
        )

        assert len(importer.parsed_transactions) == 1
        assert len(importer.parsed_transactions[0].parsed_messages) == 2

        target_message = importer.parsed_transactions[0].parsed_messages[1]
        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target_taric_object = target_message.taric_object
        assert target_taric_object.sid == "5"
        assert target_taric_object.description == "some description"

        assert importer.issues() == []

    def test_import_update(self, superuser):
        preload_import("additional_code_type_description_CREATE.xml", __file__, True)
        importer = preload_import(
            "additional_code_type_description_UPDATE.xml",
            __file__,
        )

        assert len(importer.parsed_transactions) == 1
        assert len(importer.parsed_transactions[0].parsed_messages) == 1

        target_message = importer.parsed_transactions[0].parsed_messages[0]
        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target_taric_object = target_message.taric_object
        assert target_taric_object.sid == "5"
        assert target_taric_object.description == "some description that changed"

        assert importer.issues() == []

    def test_import_delete(self, superuser):
        preload_import("additional_code_type_description_CREATE.xml", __file__, True)
        importer = preload_import(
            "additional_code_type_description_DELETE.xml",
            __file__,
        )

        assert importer.can_save()

        # check for issues
        assert len(importer.issues()) == 1

        assert (
            "Children of Taric objects of type AdditionalCodeType can't be deleted directly"
            in str(importer.issues()[0])
        )

    def test_import_invalid_type(self, superuser):
        importer = preload_import(
            "additional_code_type_description_without_type_CREATE.xml",
            __file__,
        )

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

        target_taric_object = target_message.taric_object
        assert target_taric_object.sid == "12"
        assert target_taric_object.description == "some description"

        assert len(importer.issues()) == 1
        assert (
            str(target_taric_object.issues[0])
            == "ERROR: Missing expected parent object NewAdditionalCodeTypeParser\n"
            "  additional.code.type.description > additional.code.type\n"
            "  link_data: {'sid': '12'}"
        )
