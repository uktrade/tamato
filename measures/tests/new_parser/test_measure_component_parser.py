import pytest

from commodities.new_import_parsers import *

# note : need to import these objects to make them available to the parser
from common.tests.util import preload_import
from geo_areas.models import GeographicalAreaDescription
from geo_areas.new_import_parsers import *
from measures.new_import_parsers import *
from regulations.new_import_parsers import *

pytestmark = pytest.mark.django_db


@pytest.mark.new_importer
class TestNewMeasureComponentParser:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="measure.component" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="measure.sid" type="SID"/>
                    <xs:element name="duty.expression.id" type="DutyExpressionId"/>
                    <xs:element name="duty.amount" type="DutyAmount" minOccurs="0"/>
                    <xs:element name="monetary.unit.code" type="MonetaryUnitCode" minOccurs="0"/>
                    <xs:element name="measurement.unit.code" type="MeasurementUnitCode" minOccurs="0"/>
                    <xs:element name="measurement.unit.qualifier.code" type="MeasurementUnitQualifierCode" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    target_parser_class = NewMeasureComponentParser

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "measure_sid": "5",
            "duty_expression_id": "4",
            "duty_amount": "12.93",
            "monetary_unit_code": "ABC",
            "measurement_unit_code": "3",
            "measurement_unit_qualifier_code": "2",
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
        assert target.component_measure__sid == 5
        assert target.duty_expression__sid == 4
        assert target.duty_amount == 12.93
        assert target.monetary_unit__code == "ABC"
        assert target.component_measurement__measurement_unit__code == "3"
        assert target.component_measurement__measurement_unit_qualifier__code == "2"

    def test_import(self, superuser):
        importer = preload_import("measure_component_CREATE.xml", __file__)

        assert len(importer.parsed_transactions) == 14

        target_message = importer.parsed_transactions[13].parsed_messages[0]
        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target = target_message.taric_object

        assert target.component_measure__sid == 99
        assert target.duty_expression__sid == 7
        assert target.duty_amount == 12.77
        assert target.monetary_unit__code == "ZZZ"
        assert target.component_measurement__measurement_unit__code == "XYZ"
        assert target.component_measurement__measurement_unit_qualifier__code == "F"

        assert len(importer.issues()) == 0

        assert GeographicalAreaDescription.objects.all().count() == 1

    def test_import_update(self, superuser):
        preload_import("measure_component_CREATE.xml", __file__, True)
        importer = preload_import("measure_component_UPDATE.xml", __file__)

        target_message = importer.parsed_transactions[0].parsed_messages[0]
        target = target_message.taric_object

        assert target.component_measure__sid == 99
        assert target.duty_expression__sid == 7
        assert target.duty_amount == 17.5
        assert target.monetary_unit__code == "ZZZ"
        assert target.component_measurement__measurement_unit__code == "XYZ"
        assert target.component_measurement__measurement_unit_qualifier__code == "F"

        assert len(importer.issues()) == 0

        assert GeographicalAreaDescription.objects.all().count() == 2
