from datetime import date

import pytest

from common.tests.util import preload_import
from common.validators import UpdateType
from taric_parsers.parsers.additional_code_parsers import *

pytestmark = pytest.mark.django_db


@pytest.mark.importer_v2
class TestAdditionalCodeDescriptionParserV2:
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

    target_parser_class = AdditionalCodeDescriptionParserV2

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
        assert type(target_taric_object) == AdditionalCodeDescriptionParserV2
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
        assert type(target_taric_object) == AdditionalCodeDescriptionParserV2
        assert target_taric_object.sid == 5
        assert target_taric_object.described_additionalcode__sid == 1
        assert target_taric_object.described_additionalcode__type__sid == "9"
        assert target_taric_object.described_additionalcode__code == "2"
        assert target_taric_object.description == "some description change"
        assert (
            target_taric_object.validity_start is None
        )  # No data in update for period

        assert importer.issues() == []

        assert AdditionalCodeDescription.objects.all().count() == 2

    def test_import_delete(self, superuser):
        preload_import("additional_code_description_CREATE.xml", __file__, True)
        importer = preload_import("additional_code_description_DELETE.xml", __file__)

        assert importer.can_save()
        assert importer.issues() == []
        assert AdditionalCodeDescription.objects.all().count() == 2
        assert (
            AdditionalCodeDescription.objects.all().last().update_type
            == UpdateType.DELETE
        )

    def test_import_invalid_additional_code(self, superuser):
        importer = preload_import(
            "additional_code_description_invalid_additional_code_CREATE.xml",
            __file__,
        )

        assert len(importer.parsed_transactions) == 1
        assert len(importer.parsed_transactions[0].parsed_messages) == 1

        target_message = importer.parsed_transactions[0].parsed_messages[0]

        assert (
            target_message.record_code == AdditionalCodeDescriptionParserV2.record_code
        )
        assert (
            target_message.subrecord_code
            == AdditionalCodeDescriptionParserV2.subrecord_code
        )
        assert type(target_message.taric_object) == AdditionalCodeDescriptionParserV2

        target_taric_object = target_message.taric_object
        assert target_taric_object.sid == 5
        assert target_taric_object.described_additionalcode__sid == 1
        assert target_taric_object.described_additionalcode__type__sid == "12"
        assert target_taric_object.described_additionalcode__code == "111"
        assert target_taric_object.description == "some description"

        assert len(importer.issues()) == 1

        assert (
            "ERROR: Missing expected child object AdditionalCodeDescriptionPeriodParserV2"
            in str(importer.issues()[0])
        )
        assert (
            "additional.code.description > additional.code.description.period"
            in str(importer.issues()[0])
        )
        assert "link_data: {}" in str(importer.issues()[0])
