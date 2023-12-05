import pytest

# note : need to import these objects to make them available to the parser
from common.tests.util import preload_import
from measures.models import MeasureCondition
from taric_parsers.parsers.measure_parser import *

pytestmark = pytest.mark.django_db


@pytest.mark.importer_v2
class TestMeasureConditionParserV2:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="measure.condition" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="measure.condition.sid" type="SID"/>
                    <xs:element name="measure.sid" type="SID"/>
                    <xs:element name="condition.code" type="ConditionCode"/>
                    <xs:element name="component.sequence.number" type="ComponentSequenceNumber"/>
                    <xs:element name="condition.duty.amount" type="DutyAmount" minOccurs="0"/>
                    <xs:element name="condition.monetary.unit.code" type="MonetaryUnitCode" minOccurs="0"/>
                    <xs:element name="condition.measurement.unit.code" type="MeasurementUnitCode" minOccurs="0"/>
                    <xs:element name="condition.measurement.unit.qualifier.code" type="MeasurementUnitQualifierCode" minOccurs="0"/>
                    <xs:element name="action.code" type="ActionCode" minOccurs="0"/>
                    <xs:element name="certificate.type.code" type="CertificateTypeCode" minOccurs="0"/>
                    <xs:element name="certificate.code" type="CertificateCode" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    target_parser_class = MeasureConditionParserV2

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "measure_condition_sid": "7",
            "measure_sid": "8",
            "condition_code": "AA",
            "component_sequence_number": "3",
            "condition_duty_amount": "12.5",
            "condition_monetary_unit_code": "GBP",
            "condition_measurement_unit_code": "ABC",
            "condition_measurement_unit_qualifier_code": "A",
            "action_code": "XYZ",
            "certificate_type_code": "A",
            "certificate_code": "CER",
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
        assert target.dependent_measure__sid == 8
        assert target.condition_code__code == "AA"
        assert target.component_sequence_number == 3
        assert target.duty_amount == 12.5
        assert target.monetary_unit__code == "GBP"
        assert target.condition_measurement__measurement_unit__code == "ABC"
        assert target.condition_measurement__measurement_unit_qualifier__code == "A"
        assert target.action__code == "XYZ"
        assert target.required_certificate__certificate_type__sid == "A"
        assert target.required_certificate__sid == "CER"

    def test_import(self, superuser):
        importer = preload_import("measure_condition_CREATE.xml", __file__)

        assert len(importer.parsed_transactions) == 21

        target_message = importer.parsed_transactions[20].parsed_messages[0]
        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target = target_message.taric_object

        assert target.sid == 5
        assert target.dependent_measure__sid == 99
        assert target.condition_code__code == "A"
        assert target.component_sequence_number == 5
        assert target.duty_amount == 12.77
        assert target.monetary_unit__code == "ZZZ"
        assert target.condition_measurement__measurement_unit__code == "XXX"
        assert target.condition_measurement__measurement_unit_qualifier__code == "A"
        assert target.action__code == "ABC"
        assert target.required_certificate__certificate_type__sid == "A"
        assert target.required_certificate__sid == "123"

        assert len(importer.issues()) == 0

        assert MeasureCondition.objects.all().count() == 1

    def test_import_update(self, superuser):
        preload_import("measure_condition_CREATE.xml", __file__, True)
        importer = preload_import("measure_condition_UPDATE.xml", __file__)

        target_message = importer.parsed_transactions[0].parsed_messages[0]

        target = target_message.taric_object

        assert target.sid == 5
        assert target.dependent_measure__sid == 99
        assert target.condition_code__code == "A"
        assert target.component_sequence_number == 5
        assert target.duty_amount == 99.99
        assert target.monetary_unit__code == "ZZZ"
        assert target.condition_measurement__measurement_unit__code == "XXX"
        assert target.condition_measurement__measurement_unit_qualifier__code == "A"
        assert target.action__code == "ABC"
        assert target.required_certificate__certificate_type__sid == "A"
        assert target.required_certificate__sid == "123"

        assert len(importer.issues()) == 0

        assert MeasureCondition.objects.all().count() == 2

    def test_import_delete(self, superuser):
        preload_import("measure_condition_CREATE.xml", __file__, True)
        importer = preload_import("measure_condition_DELETE.xml", __file__)

        assert len(importer.issues()) == 0
        assert importer.can_save()

        assert MeasureCondition.objects.all().count() == 2
