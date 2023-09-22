from datetime import date

import pytest

from additional_codes.new_import_parsers import NewAdditionalCodeTypeParser
from common.tests import factories
from common.tests.util import get_test_xml_file
from importer import new_importer
from workbaskets.validators import WorkflowStatus

pytestmark = pytest.mark.django_db


@pytest.mark.new_importer
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

    target_parser_class = NewAdditionalCodeTypeParser

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "additional_code_type_id": "123",
            "validity_start_date": "2023-01-22",
            "validity_end_date": "2024-01-22",
            "application_code": "123",
            "meursing_table_plan_id": "123",  # this property is not imported
        }

        target = self.target_parser_class()

        target.populate(
            1,  # transaction id
            target.record_code,
            target.subrecord_code,
            1,  # sequence number
            expected_data_example,
        )

        assert target.sid == "123"
        assert target.valid_between_lower == date(2023, 1, 22)
        assert target.valid_between_upper == date(2024, 1, 22)
        assert target.application_code == "123"

    def test_import(self, superuser):
        file_to_import = get_test_xml_file("additional_code_type_CREATE.xml", __file__)

        workbasket = factories.WorkBasketFactory.create(status=WorkflowStatus.EDITING)
        import_batch = factories.ImportBatchFactory.create(workbasket=workbasket)

        importer = new_importer.NewImporter(
            import_batch=import_batch,
            taric3_file=file_to_import,
            import_title="Importing stuff",
            author_username=superuser.username,
        )

        assert len(importer.parsed_transactions) == 1
        assert len(importer.parsed_transactions[0].parsed_messages) == 2

        target_message = importer.parsed_transactions[0].parsed_messages[1]
        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        # check properties
        target_taric_object = target_message.taric_object
        assert target_taric_object.sid == "1"
        assert target_taric_object.valid_between_lower == date(2021, 1, 1)
        assert target_taric_object.valid_between_upper == date(2021, 12, 31)
        assert target_taric_object.application_code == "111"

        assert len(importer.issues()) == 0

    def test_import_no_description(self, superuser):
        file_to_import = get_test_xml_file(
            "additional_code_type_no_description_CREATE.xml",
            __file__,
        )

        workbasket = factories.WorkBasketFactory.create(status=WorkflowStatus.EDITING)
        import_batch = factories.ImportBatchFactory.create(workbasket=workbasket)

        importer = new_importer.NewImporter(
            import_batch=import_batch,
            taric3_file=file_to_import,
            import_title="Importing stuff",
            author_username=superuser.username,
        )

        assert len(importer.parsed_transactions) == 1
        assert len(importer.parsed_transactions[0].parsed_messages) == 1

        target_message = importer.parsed_transactions[0].parsed_messages[0]
        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        # check properties
        target_taric_object = target_message.taric_object
        assert target_taric_object.sid == "5"
        assert target_taric_object.valid_between_lower == date(2021, 1, 1)
        assert target_taric_object.valid_between_upper == date(2021, 12, 31)
        assert target_taric_object.application_code == "111"

        assert len(importer.issues()) == 1

        assert (
            str(importer.issues()[0])
            == "ERROR: Missing expected child object NewAdditionalCodeTypeDescriptionParser\n  "
            "additional.code.type > additional.code.type.description\n  "
            "link_data: {}"
        )
