from datetime import date

import pytest

from additional_codes.new_import_parsers import (
    NewFootnoteAssociationAdditionalCodeParser,
)
from importer import new_importer

pytestmark = pytest.mark.django_db


class TestNewAdditionalCodeTypeParser:
    """
    Example XML:

    .. code-block: XML

        <xs:element name="footnote.association.additional.code" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="additional.code.sid" type="SID"/>
                    <xs:element name="footnote.type.id" type="FootnoteTypeId"/>
                    <xs:element name="footnote.id" type="FootnoteId"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                    <xs:element name="additional.code.type.id" type="AdditionalCodeTypeId"/>
                    <xs:element name="additional.code" type="AdditionalCode"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "additional_code_sid": "111",
            "footnote_type_id": "444",
            "footnote_id": "555",
            "validity_start_date": "2023-01-22",
            "validity_end_date": "2024-01-22",
            "additional_code": "666",
            "additional_code_type_id": "777",
        }

        target = NewFootnoteAssociationAdditionalCodeParser()

        target.populate(
            1,  # transaction id
            target.record_code,
            target.subrecord_code,
            1,  # sequence number
            expected_data_example,
        )

        # verify all properties
        assert (
            target.additional_code__sid == 111
        )  # converts "additional.code.type.id" to sid
        assert target.associated_footnote__footnote_type__id == "444"
        assert target.associated_footnote__footnote_id == "555"
        assert target.valid_between_lower == date(2023, 1, 22)
        assert target.valid_between_upper == date(2024, 1, 22)
        assert target.additional_code__code == "666"
        assert target.additional_code__type__sid == 777

    def test_import(self, superuser):
        file_to_import = (
            "./importer_examples/footnote_association_additional_code_CREATE.xml"
        )

        importer = new_importer.NewImporter(
            file_to_import,
            "Importing stuff",
            superuser.username,
        )

        # check there is one AdditionalCodeType imported
        assert len(importer.parsed_transactions) == 1
        assert len(importer.parsed_transactions[0].parsed_messages) == 5

        target_message = importer.parsed_transactions[0].parsed_messages[2]
        assert (
            target_message.record_code
            == NewFootnoteAssociationAdditionalCodeParser.record_code
        )
        assert (
            target_message.subrecord_code
            == NewFootnoteAssociationAdditionalCodeParser.subrecord_code
        )
        assert (
            type(target_message.taric_object)
            == NewFootnoteAssociationAdditionalCodeParser
        )

        # check properties
        target_taric_object = target_message.taric_object
        assert target_taric_object.additional_code__sid == 1
        assert target_taric_object.associated_footnote__footnote_type__id == "7"
        assert target_taric_object.associated_footnote__footnote_id == "9"
        assert target_taric_object.valid_between_upper == date(2021, 1, 1)
        assert target_taric_object.valid_between_lower == date(2021, 1, 1)
        assert target_taric_object.additional_code__type__sid == 12
        assert target_taric_object.additional_code__code == "111"

        for message in importer.parsed_transactions[0].parsed_messages:
            assert len(message.taric_object.issues) == 0

    def test_import_invalid_footnote(self, superuser):
        file_to_import = "./importer_examples/footnote_association_additional_code_invalid_footnote_CREATE.xml"

        importer = new_importer.NewImporter(
            file_to_import,
            "Importing stuff",
            superuser.username,
        )

        target_message = importer.parsed_transactions[0].parsed_messages[2]
        target_taric_object = target_message.taric_object

        assert len(target_taric_object.issues) == 1
        assert (
            str(target_taric_object.issues[0])
            == "ERROR: No matches for possible related taric object\n"
            "  footnote.association.additional.code > footnote\n"
            "  link_data: {'footnote_type_id': '7', 'footnote_id': '9'}"
        )
