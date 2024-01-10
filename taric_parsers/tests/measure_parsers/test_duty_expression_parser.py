import pytest

# note : need to import these objects to make them available to the parser
from common.tests.util import preload_import
from measures.models import DutyExpression
from taric_parsers.parsers.geo_area_parser import *
from taric_parsers.parsers.measure_parser import *

pytestmark = pytest.mark.django_db


@pytest.mark.importer_v2
class TestDutyExpressionParserV2:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="duty.expression" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="duty.expression.id" type="DutyExpressionId"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                    <xs:element name="duty.amount.applicability.code" type="DutyAmountApplicabilityCode"/>
                    <xs:element name="measurement.unit.applicability.code" type="MeasurementUnitApplicabilityCode"/>
                    <xs:element name="monetary.unit.applicability.code" type="MonetaryUnitApplicabilityCode"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    target_parser_class = DutyExpressionParserV2

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "duty_expression_id": "7",
            "validity_start_date": "2021-01-01",
            "validity_end_date": "2022-01-01",
            "duty_amount_applicability_code": "8",
            "measurement_unit_applicability_code": "9",
            "monetary_unit_applicability_code": "10",
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

        assert target.sid == 7
        assert target.valid_between_lower == date(2021, 1, 1)
        assert target.valid_between_upper == date(2022, 1, 1)
        assert target.duty_amount_applicability_code == 8
        assert target.measurement_unit_applicability_code == 9
        assert target.monetary_unit_applicability_code == 10

    def test_import(self, superuser):
        importer = preload_import("duty_expression_CREATE.xml", __file__)

        assert len(importer.parsed_transactions) == 1

        target_message = importer.parsed_transactions[0].parsed_messages[0]
        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target = target_message.taric_object

        assert target.sid == 7
        assert target.valid_between_lower == date(2021, 1, 1)
        assert target.valid_between_upper == date(2022, 1, 1)
        assert target.duty_amount_applicability_code == 8
        assert target.measurement_unit_applicability_code == 9
        assert target.monetary_unit_applicability_code == 10

        assert len(importer.issues()) == 0

        assert DutyExpression.objects.all().count() == 1

    def test_import_update(self, superuser):
        preload_import("duty_expression_CREATE.xml", __file__, True)
        importer = preload_import("duty_expression_UPDATE.xml", __file__)

        target_message = importer.parsed_transactions[0].parsed_messages[0]

        target = target_message.taric_object

        assert target.sid == 7
        assert target.valid_between_lower == date(2021, 1, 21)
        assert target.valid_between_upper == date(2022, 1, 1)
        assert target.duty_amount_applicability_code == 8
        assert target.measurement_unit_applicability_code == 9
        assert target.monetary_unit_applicability_code == 10

        assert len(importer.issues()) == 0

        assert DutyExpression.objects.all().count() == 2

    def test_import_delete(self, superuser):
        preload_import("duty_expression_CREATE.xml", __file__, True)
        importer = preload_import("duty_expression_DELETE.xml", __file__)

        assert len(importer.issues()) == 0
        assert importer.issues() == []

        assert DutyExpression.objects.all().count() == 2
