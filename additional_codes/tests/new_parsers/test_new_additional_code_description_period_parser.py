from datetime import date

import pytest

from additional_codes.new_import_parsers import NewAdditionalCodeDescriptionPeriodParser
from importer import new_importer

pytestmark = pytest.mark.django_db


class TestNewAdditionalCodeDescriptionPeriodParser:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="additional.code.description.period" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="additional.code.description.period.sid" type="SID"/>
                    <xs:element name="additional.code.sid" type="SID"/>
                    <xs:element name="additional.code.type.id" type="AdditionalCodeTypeId"/>
                    <xs:element name="additional.code" type="AdditionalCode"/>
                    <xs:element name="validity.start.date" type="Date"/>
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
            "validity_start_date": "2023-01-22",
        }

        target = NewAdditionalCodeDescriptionPeriodParser()

        target.populate(
            1,  # transaction id
            target.record_code,
            target.subrecord_code,
            1,  # sequence number
            expected_data_example,
        )

        # verify all properties
        assert target.sid == 123  # converts "additional.code.type.id" to sid
        assert target.validity_start == date(2023, 1, 22)
        assert target.described_additionalcode__sid == 123
        assert target.described_additionalcode__type__sid == 123
        assert target.described_additionalcode__code == "123"

    def test_import(self, superuser):
        file_to_import = (
            "./importer_examples/additional_code_description_period_CREATE.xml"
        )

        importer = new_importer.NewImporter(
            file_to_import,
            "Importing stuff",
            superuser.username,
        )

        # check there is one AdditionalCodeType imported
        assert len(importer.parsed_transactions) == 1
        assert len(importer.parsed_transactions[0].parsed_messages) == 4

        target_message = importer.parsed_transactions[0].parsed_messages[2]

        assert (
            target_message.record_code
            == NewAdditionalCodeDescriptionPeriodParser.record_code
        )
        assert (
            target_message.subrecord_code
            == NewAdditionalCodeDescriptionPeriodParser.subrecord_code
        )
        assert (
            type(target_message.taric_object)
            == NewAdditionalCodeDescriptionPeriodParser
        )

        # check properties for additional code
        target_taric_object = target_message.taric_object
        assert target_taric_object.sid == 5
        assert target_taric_object.described_additionalcode__sid == 1
        assert target_taric_object.described_additionalcode__type__sid == 12
        assert target_taric_object.described_additionalcode__code == "111"
        assert target_taric_object.validity_start == date(2021, 1, 1)

        for message in importer.parsed_transactions[0].parsed_messages:
            # check for issues
            assert len(message.taric_object.issues) == 0

    def test_import_no_description(self, superuser):
        file_to_import = "./importer_examples/additional_code_description_period_without_description_CREATE.xml"

        importer = new_importer.NewImporter(
            file_to_import,
            "Importing stuff",
            superuser.username,
        )

        # check there is one AdditionalCodeType imported
        assert len(importer.parsed_transactions) == 1
        assert len(importer.parsed_transactions[0].parsed_messages) == 3

        target_message = importer.parsed_transactions[0].parsed_messages[2]

        assert (
            target_message.record_code
            == NewAdditionalCodeDescriptionPeriodParser.record_code
        )
        assert (
            target_message.subrecord_code
            == NewAdditionalCodeDescriptionPeriodParser.subrecord_code
        )
        assert (
            type(target_message.taric_object)
            == NewAdditionalCodeDescriptionPeriodParser
        )

        # check properties for additional code
        target_taric_object = target_message.taric_object
        assert target_taric_object.sid == 5
        assert target_taric_object.described_additionalcode__sid == 1
        assert target_taric_object.described_additionalcode__type__sid == 12
        assert target_taric_object.described_additionalcode__code == "111"
        assert target_taric_object.validity_start == date(2021, 1, 1)

        assert len(target_taric_object.issues) == 1
        assert (
            str(target_taric_object.issues[0])
            == "ERROR: No matches for possible related taric object\n"
            "  additional.code.description.period > "
            "additional.code.description\n"
            "  link_data: {'sid': 5}"
        )
