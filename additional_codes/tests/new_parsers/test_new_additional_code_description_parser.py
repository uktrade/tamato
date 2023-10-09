from datetime import date

import pytest

from additional_codes.models import AdditionalCode
from additional_codes.models import AdditionalCodeDescription
from additional_codes.models import AdditionalCodeType
from additional_codes.new_import_parsers import NewAdditionalCodeDescriptionParser
from common.tests.util import preload_import

pytestmark = pytest.mark.django_db


@pytest.mark.new_importer
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

    target_parser_class = NewAdditionalCodeDescriptionParser

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "additional_code_description_period_sid": "123",
            "additional_code_sid": "123",
            "additional_code_type_id": "A",
            "additional_code": "123",
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

        # verify all properties
        assert target.sid == 123
        assert target.described_additionalcode__sid == 123
        assert target.described_additionalcode__type__sid == "A"
        assert target.described_additionalcode__code == "123"
        assert target.description == "some description"

    def test_import_create(self, superuser):
        importer = preload_import("additional_code_description_CREATE.xml", __file__)

        assert len(importer.parsed_transactions) == 1
        assert len(importer.parsed_transactions[0].parsed_messages) == 5

        target_message = importer.parsed_transactions[0].parsed_messages[4]

        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target_taric_object = target_message.taric_object

        for message in importer.parsed_transactions[0].parsed_messages:
            assert len(message.taric_object.issues) == 0

        assert AdditionalCode.objects.all().count() == 1
        assert AdditionalCodeType.objects.all().count() == 1
        assert AdditionalCodeDescription.objects.all().count() == 1

        assert importer.can_save()
        assert type(target_taric_object) == NewAdditionalCodeDescriptionParser
        assert target_taric_object.sid == 5
        assert target_taric_object.described_additionalcode__sid == 1
        assert target_taric_object.described_additionalcode__type__sid == "9"
        assert target_taric_object.described_additionalcode__code == "2"
        assert target_taric_object.description == "some description"
        assert target_taric_object.validity_start == date(2021, 1, 1)

        assert importer.issues() == []

    def test_import_update(self, superuser):
        preload_import("additional_code_description_CREATE.xml", __file__, True)
        importer = preload_import("additional_code_description_UPDATE.xml", __file__)

        target_message = importer.parsed_transactions[0].parsed_messages[0]
        target_taric_object = target_message.taric_object

        assert importer.can_save()
        assert type(target_taric_object) == NewAdditionalCodeDescriptionParser
        assert target_taric_object.sid == 5
        assert target_taric_object.described_additionalcode__sid == 1
        assert target_taric_object.described_additionalcode__type__sid == "9"
        assert target_taric_object.described_additionalcode__code == "2"
        assert target_taric_object.description == "some description change"
        assert (
            target_taric_object.validity_start is None
        )  # No data in update for period

        assert importer.issues() == []

    def test_import_invalid_additional_code(self, superuser):
        importer = preload_import(
            "additional_code_description_invalid_additional_code_CREATE.xml",
            __file__,
        )

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

        target_taric_object = target_message.taric_object
        assert target_taric_object.sid == 5
        assert target_taric_object.described_additionalcode__sid == 1
        assert target_taric_object.described_additionalcode__type__sid == "12"
        assert target_taric_object.described_additionalcode__code == "111"
        assert target_taric_object.description == "some description"

        issue_1 = target_taric_object.issues[0]

        assert (
            str(issue_1)
            == "ERROR: Missing expected child object NewAdditionalCodeDescriptionPeriodParser\n"
            "  additional.code.description > additional.code.description.period\n"
            "  link_data: {}"
        )
