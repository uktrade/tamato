from datetime import date

import pytest

from additional_codes.new_import_parsers import NewAdditionalCodeTypeParser
from importer import new_importer

pytestmark = pytest.mark.django_db


class TestNewAdditionalCodeTypeParser:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="additional.code.type" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="additional.code.type.id" type="AdditionalCodeTypeId"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                    <xs:element name="application.code" type="ApplicationCodeAdditionalCode"/>
                    <xs:element name="meursing.table.plan.id" type="MeursingTablePlanId" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "additional_code_type_id": "123",
            "validity_start_date": "2023-01-22",
            "validity_end_date": "2024-01-22",
            "application_code": "123",
            # "meursing_table_plan_id": "123" - this property is not imported
        }

        target = NewAdditionalCodeTypeParser()

        target.populate(
            1,  # transaction id
            target.record_code,
            target.subrecord_code,
            1,  # sequence number
            expected_data_example,
        )

        # verify all properties
        assert target.sid == 123  # converts "additional.code.type.id" to sid
        assert target.valid_between_lower == date(2023, 1, 22)
        assert target.valid_between_upper == date(2024, 1, 22)
        assert target.application_code == "123"

    def test_import(self):
        file_to_import = "./importer_examples/additional_code_type_CREATE.xml"

        importer = new_importer.NewImporter(file_to_import)

        # check there is one AdditionalCodeType imported
        assert len(importer.parsed_transactions) == 1
        assert len(importer.parsed_transactions[0].parsed_messages) == 1

        target_message = importer.parsed_transactions[0].parsed_messages[0]
        assert target_message.record_code == NewAdditionalCodeTypeParser.record_code
        assert (
            target_message.subrecord_code == NewAdditionalCodeTypeParser.subrecord_code
        )
        assert type(target_message.taric_object) == NewAdditionalCodeTypeParser

        # check properties
        target_taric_object = target_message.taric_object
        assert target_taric_object.sid == 12
        assert target_taric_object.valid_between_lower == date(2021, 1, 1)
        assert target_taric_object.valid_between_upper == date(2021, 12, 31)
        assert target_taric_object.application_code == "111"

        for message in importer.parsed_transactions[0].parsed_messages:
            assert len(message.taric_object.issues) == 0