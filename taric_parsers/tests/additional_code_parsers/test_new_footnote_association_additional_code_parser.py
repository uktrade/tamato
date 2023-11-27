from datetime import date

import pytest

from additional_codes.models import *
from common.tests.util import preload_import
from common.validators import UpdateType
from taric_parsers.parsers.additional_code_parsers import *
from taric_parsers.parsers.footnote_parser import *

pytestmark = pytest.mark.django_db


@pytest.mark.importer_v2
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

    target_parser_class = NewFootnoteAssociationAdditionalCodeParser

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "additional_code_sid": "111",
            "footnote_type_id": "5",
            "footnote_id": "555",
            "validity_start_date": "2023-01-22",
            "validity_end_date": "2024-01-22",
            "additional_code": "666",
            "additional_code_type_id": "Z",
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
        assert target.additional_code__sid == 111
        assert target.associated_footnote__footnote_type__footnote_type_id == 5
        assert target.associated_footnote__footnote_id == "555"
        assert target.valid_between_lower == date(2023, 1, 22)
        assert target.valid_between_upper == date(2024, 1, 22)
        assert target.additional_code__code == "666"
        assert target.additional_code__type__sid == "Z"

    def test_import(self, superuser):
        importer = preload_import(
            "footnote_association_additional_code_CREATE.xml",
            __file__,
        )

        assert len(importer.parsed_transactions) == 3

        target_message = importer.parsed_transactions[2].parsed_messages[0]
        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        # check properties
        target_taric_object = target_message.taric_object
        assert target_taric_object.additional_code__sid == 1
        assert (
            target_taric_object.associated_footnote__footnote_type__footnote_type_id
            == 7
        )
        assert target_taric_object.associated_footnote__footnote_id == "4"
        assert target_taric_object.valid_between_upper == date(2021, 1, 1)
        assert target_taric_object.valid_between_lower == date(2021, 1, 1)
        assert target_taric_object.additional_code__type__sid == "4"
        assert target_taric_object.additional_code__code == "7"

        assert importer.issues() == []

    def test_import_update(self, superuser):
        preload_import(
            "footnote_association_additional_code_CREATE.xml",
            __file__,
            True,
        )
        importer = preload_import(
            "footnote_association_additional_code_UPDATE.xml",
            __file__,
        )

        target_message = importer.parsed_transactions[0].parsed_messages[0]

        # check properties
        target_taric_object = target_message.taric_object
        assert target_taric_object.additional_code__sid == 1
        assert (
            target_taric_object.associated_footnote__footnote_type__footnote_type_id
            == 7
        )
        assert target_taric_object.associated_footnote__footnote_id == "4"
        assert target_taric_object.valid_between_upper == date(2022, 1, 1)
        assert target_taric_object.valid_between_lower == date(2021, 1, 11)
        assert target_taric_object.additional_code__type__sid == "4"
        assert target_taric_object.additional_code__code == "7"

        assert importer.issues() == []

    def test_import_delete(self, superuser):
        preload_import(
            "footnote_association_additional_code_CREATE.xml",
            __file__,
            True,
        )
        importer = preload_import(
            "footnote_association_additional_code_DELETE.xml",
            __file__,
        )
        # check for issues
        assert importer.issues() == []
        assert importer.can_save()
        assert FootnoteAssociationAdditionalCode.objects.all().count() == 2
        assert (
            FootnoteAssociationAdditionalCode.objects.all().last().update_type
            == UpdateType.DELETE
        )

    def test_import_invalid_footnote(self, superuser):
        importer = preload_import(
            "footnote_association_additional_code_invalid_footnote_CREATE.xml",
            __file__,
        )

        assert len(importer.issues()) == 2
        assert (
            str(importer.issues()[0])
            == "ERROR: Missing expected child object NewAdditionalCodeTypeDescriptionParser\n"
            "  additional.code.type > additional.code.type.description\n"
            "  link_data: {}"
        )
        assert (
            str(importer.issues()[1])
            == "ERROR: Missing expected child object NewFootnoteTypeDescriptionParser\n"
            "  footnote.type > footnote.type.description\n"
            "  link_data: {}"
        )
