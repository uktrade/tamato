import pytest

# note : need to import these objects to make them available to the parser
from common.tests.util import preload_import
from geo_areas.new_import_parsers import *
from measures.models import MeasureType
from measures.new_import_parsers import NewMeasureTypeParser

pytestmark = pytest.mark.django_db


@pytest.mark.new_importer
class TestNewMeasureTypeParser:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="measure.type" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="measure.type.id" type="MeasureTypeId"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                    <xs:element name="trade.movement.code" type="TradeMovementCode"/>
                    <xs:element name="priority.code" type="PriorityCode"/>
                    <xs:element name="measure.component.applicable.code" type="MeasurementUnitApplicabilityCode"/>
                    <xs:element name="origin.dest.code" type="OriginCode"/>
                    <xs:element name="order.number.capture.code" type="OrderNumberCaptureCode"/>
                    <xs:element name="measure.explosion.level" type="MeasureExplosionLevel"/>
                    <xs:element name="measure.type.series.id" type="MeasureTypeSeriesId"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    target_parser_class = NewMeasureTypeParser

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "measure_type_id": "ZZZ",
            "trade_movement_code": "1",
            "priority_code": "2",
            "measure_component_applicable_code": "3",
            "origin_dest_code": "4",
            "order_number_capture_code": "5",
            "measure_explosion_level": "6",
            "measure_type_series_id": "7",
            "validity_start_date": "2021-01-01",
            "validity_end_date": "2022-01-01",
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
        assert target.sid == "ZZZ"
        assert target.trade_movement_code == 1
        assert target.priority_code == 2
        assert target.measure_component_applicability_code == 3
        assert target.origin_destination_code == 4
        assert target.order_number_capture_code == 5
        assert target.measure_explosion_level == 6
        assert target.measure_type_series__sid == "7"
        assert target.valid_between_lower == date(2021, 1, 1)
        assert target.valid_between_upper == date(2022, 1, 1)

    def test_import(self, superuser):
        importer = preload_import("measure_type_CREATE.xml", __file__)

        assert len(importer.parsed_transactions) == 2

        target_message = importer.parsed_transactions[1].parsed_messages[0]
        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target = target_message.taric_object

        assert target.sid == "ZZZ"
        assert target.trade_movement_code == 1
        assert target.priority_code == 2
        assert target.measure_component_applicability_code == 3
        assert target.origin_destination_code == 4
        assert target.order_number_capture_code == 5
        assert target.measure_explosion_level == 6
        assert target.measure_type_series__sid == "A"
        assert target.valid_between_lower == date(2021, 1, 1)
        assert target.valid_between_upper == date(2022, 1, 1)

        assert len(importer.issues()) == 0

        assert MeasureType.objects.all().count() == 1

    def test_import_update(self, superuser):
        preload_import("measure_type_CREATE.xml", __file__, True)
        importer = preload_import("measure_type_UPDATE.xml", __file__)

        target_message = importer.parsed_transactions[0].parsed_messages[0]
        target = target_message.taric_object

        assert target.sid == "ZZZ"
        assert target.trade_movement_code == 1
        assert target.priority_code == 2
        assert target.measure_component_applicability_code == 3
        assert target.origin_destination_code == 4
        assert target.order_number_capture_code == 5
        assert target.measure_explosion_level == 6
        assert target.measure_type_series__sid == "A"
        assert target.valid_between_lower == date(2021, 1, 11)
        assert target.valid_between_upper == date(2022, 1, 1)

        assert len(importer.issues()) == 0

        assert MeasureType.objects.all().count() == 2

    def test_import_delete(self, superuser):
        preload_import("measure_type_CREATE.xml", __file__, True)
        importer = preload_import("measure_type_DELETE.xml", __file__)

        assert len(importer.issues()) == 0
        assert importer.can_save()

        assert MeasureType.objects.all().count() == 2
