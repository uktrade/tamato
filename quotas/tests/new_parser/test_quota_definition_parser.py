from datetime import date

import pytest

from common.tests import factories

# note : need to import these objects to make them available to the parser
from common.tests.util import get_test_xml_file
from importer import new_importer
from measures.new_import_parsers import *
from quotas.models import QuotaDefinition
from quotas.new_import_parsers import *
from workbaskets.validators import WorkflowStatus

pytestmark = pytest.mark.django_db


@pytest.mark.new_importer
class TestNewQuotaDefinitionParser:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="quota.definition" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="quota.definition.sid" type="SID"/>
                    <xs:element name="quota.order.number.id" type="OrderNumber"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                    <xs:element name="quota.order.number.sid" type="SID"/>
                    <xs:element name="volume" type="QuotaAmount"/>
                    <xs:element name="initial.volume" type="QuotaAmount"/>
                    <xs:element name="monetary.unit.code" type="MonetaryUnitCode" minOccurs="0"/>
                    <xs:element name="measurement.unit.code" type="MeasurementUnitCode" minOccurs="0"/>
                    <xs:element name="measurement.unit.qualifier.code" type="MeasurementUnitQualifierCode" minOccurs="0"/>
                    <xs:element name="maximum.precision" type="QuotaPrecision"/>
                    <xs:element name="critical.state" type="QuotaCriticalStateCode"/>
                    <xs:element name="critical.threshold" type="QuotaCriticalTreshold"/>
                    <xs:element name="description" type="ShortDescription" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    target_parser_class = NewQuotaDefinitionParser

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "quota_definition_sid": "123",
            "quota_order_number_id": "010101",
            "validity_start_date": "2020-01-01",
            "validity_end_date": "2020-12-01",
            "quota_order_number_sid": "234",
            "volume": "33000",
            "initial_volume": "23000",
            "monetary_unit_code": "ABC",
            "measurement_unit_code": "EFG",
            "measurement_unit_qualifier_code": "Z",
            "maximum_precision": "7",
            "critical_state": "0",
            "critical_threshold": "7",
            "description": "Some Description",
        }

        target = self.target_parser_class()

        target.populate(
            1,
            target.record_code,
            target.subrecord_code,
            1,
            expected_data_example,
        )

        assert target.sid == 123
        assert target.order_number__order_number == "010101"
        assert target.valid_between_lower == date(2020, 1, 1)
        assert target.valid_between_upper == date(2020, 12, 1)
        assert target.order_number__sid == 234
        assert target.volume == 33000
        assert target.initial_volume == 23000
        assert target.monetary_unit__code == "ABC"
        assert target.measurement_unit__code == "EFG"
        assert target.measurement_unit_qualifier__code == "Z"
        assert target.maximum_precision == 7
        assert target.quota_critical == False
        assert target.quota_critical_threshold == 7
        assert target.description == "Some Description"

    def test_import(self, superuser):
        file_to_import = get_test_xml_file("quota_definition_CREATE.xml", __file__)

        workbasket = factories.WorkBasketFactory.create(status=WorkflowStatus.EDITING)
        import_batch = factories.ImportBatchFactory.create(workbasket=workbasket)

        importer = new_importer.NewImporter(
            import_batch=import_batch,
            taric3_file=file_to_import,
            import_title="Importing stuff",
            author_username=superuser.username,
        )

        # check - measurement unit variant
        assert len(importer.parsed_transactions) == 5

        target_message = importer.parsed_transactions[4].parsed_messages[0]

        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target = target_message.taric_object

        # check properties
        assert target.sid == 99
        assert target.order_number__order_number == "054515"
        assert target.valid_between_lower == date(2021, 1, 1)
        assert target.valid_between_upper == date(2022, 1, 1)
        assert target.order_number__sid == 7
        assert target.volume == 1200.0
        assert target.initial_volume == 200.0
        assert target.monetary_unit__code == None
        assert target.measurement_unit__code == "XXX"
        assert target.measurement_unit_qualifier__code == "A"
        assert target.maximum_precision == 3
        assert target.quota_critical is False
        assert target.quota_critical_threshold == 75
        assert target.description == "Some Description"

        # Check monetary unit variant
        target_message = importer.parsed_transactions[4].parsed_messages[1]
        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target = target_message.taric_object

        # check properties
        assert target.sid == 99
        assert target.order_number__order_number == "054515"
        assert target.valid_between_lower == date(2023, 1, 1)
        assert target.valid_between_upper == date(2024, 1, 1)
        assert target.order_number__sid == 7
        assert target.volume == 1200.0
        assert target.initial_volume == 200.0
        assert target.monetary_unit__code == "ZZZ"
        assert target.measurement_unit__code is None
        assert target.measurement_unit_qualifier__code is None
        assert target.maximum_precision == 3
        assert target.quota_critical is False
        assert target.quota_critical_threshold == 75
        assert target.description == "Some Description"

        assert len(importer.issues()) == 0

        assert QuotaDefinition.objects.all().count() == 2
