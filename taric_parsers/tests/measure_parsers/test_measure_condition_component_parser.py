import pytest

# note : need to import these objects to make them available to the parser
from common.tests.util import preload_import
from measures.models import MeasureConditionComponent
from taric_parsers.parsers.measure_parser import *

pytestmark = pytest.mark.django_db


@pytest.mark.importer_v2
class TestMeasureConditionComponentParserV2:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="measure.condition.component" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="measure.condition.sid" type="SID"/>
                    <xs:element name="duty.expression.id" type="DutyExpressionId"/>
                    <xs:element name="duty.amount" type="DutyAmount" minOccurs="0"/>
                    <xs:element name="monetary.unit.code" type="MonetaryUnitCode" minOccurs="0"/>
                    <xs:element name="measurement.unit.code" type="MeasurementUnitCode" minOccurs="0"/>
                    <xs:element name="measurement.unit.qualifier.code" type="MeasurementUnitQualifierCode" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    target_parser_class = MeasureConditionComponentParserV2

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "measure_condition_sid": "1",
            "duty_expression_id": "77",
            "duty_amount": "12.7",
            "monetary_unit_code": "ABC",
            "measurement_unit_code": "CDE",
            "measurement_unit_qualifier_code": "X",
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
        assert target.condition__sid == 1
        assert target.duty_expression__sid == 77
        assert target.duty_amount == 12.7
        assert target.monetary_unit__code == "ABC"
        assert target.component_measurement__measurement_unit__code == "CDE"
        assert target.component_measurement__measurement_unit_qualifier__code == "X"

    def test_import(self, superuser):
        importer = preload_import("measure_condition_component_CREATE.xml", __file__)

        assert len(importer.parsed_transactions) == 22

        target_message = importer.parsed_transactions[21].parsed_messages[0]
        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target = target_message.taric_object

        assert target.condition__sid == 5
        assert target.duty_expression__sid == 7
        assert target.duty_amount == 14.5
        assert target.monetary_unit__code == "ZZZ"
        assert target.component_measurement__measurement_unit__code == "XXX"
        assert target.component_measurement__measurement_unit_qualifier__code == "B"

        assert len(importer.issues()) == 0

        assert MeasureConditionComponent.objects.all().count() == 1

    def test_import_update(self, superuser):
        preload_import("measure_condition_component_CREATE.xml", __file__, True)
        importer = preload_import("measure_condition_component_UPDATE.xml", __file__)

        target_message = importer.parsed_transactions[0].parsed_messages[0]

        target = target_message.taric_object

        assert target.condition__sid == 5
        assert target.duty_expression__sid == 7
        assert target.duty_amount == 99.99
        assert target.monetary_unit__code == "ZZZ"
        assert target.component_measurement__measurement_unit__code == "XXX"
        assert target.component_measurement__measurement_unit_qualifier__code == "B"

        assert len(importer.issues()) == 0

        assert MeasureConditionComponent.objects.all().count() == 2

    def test_import_delete(self, superuser):
        preload_import("measure_condition_component_CREATE.xml", __file__, True)
        importer = preload_import("measure_condition_component_DELETE.xml", __file__)

        assert len(importer.issues()) == 0
        assert importer.can_save()

        assert MeasureConditionComponent.objects.all().count() == 2
