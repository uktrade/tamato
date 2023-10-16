import pytest

from additional_codes.new_import_parsers import *
from commodities.new_import_parsers import *

# note : need to import these objects to make them available to the parser
from common.tests.util import preload_import
from footnotes.new_import_parsers import *
from geo_areas.new_import_parsers import *
from measures.models import Measure
from measures.new_import_parsers import NewMeasureParser
from regulations.new_import_parsers import *

pytestmark = pytest.mark.django_db


@pytest.mark.new_importer
class TestNewMeasureParser:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="measure" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="measure.sid" type="SID"/>
                    <xs:element name="measure.type" type="MeasureTypeId"/>
                    <xs:element name="geographical.area" type="GeographicalAreaId"/>
                    <xs:element name="goods.nomenclature.item.id" type="GoodsNomenclatureItemId" minOccurs="0"/>
                    <xs:element name="additional.code.type" type="AdditionalCodeTypeId" minOccurs="0"/>
                    <xs:element name="additional.code" type="AdditionalCode" minOccurs="0"/>
                    <xs:element name="ordernumber" type="OrderNumber" minOccurs="0"/>
                    <xs:element name="reduction.indicator" type="ReductionIndicator" minOccurs="0"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="measure.generating.regulation.role" type="RegulationRoleTypeId"/>
                    <xs:element name="measure.generating.regulation.id" type="RegulationId"/>
                    <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                    <xs:element name="justification.regulation.role" type="RegulationRoleTypeId" minOccurs="0"/>
                    <xs:element name="justification.regulation.id" type="RegulationId" minOccurs="0"/>
                    <xs:element name="stopped.flag" type="StoppedFlag"/>
                    <xs:element name="geographical.area.sid" type="SID" minOccurs="0"/>
                    <xs:element name="goods.nomenclature.sid" type="SID" minOccurs="0"/>
                    <xs:element name="additional.code.sid" type="SID" minOccurs="0"/>
                    <xs:element name="export.refund.nomenclature.sid" type="SID" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    target_parser_class = NewMeasureParser

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "measure_sid": "1",
            "measure_type": "AA",
            "geographical_area": "BB",
            "geographical_area_sid": "99",
            "goods_nomenclature_item_id": "1122334455",
            "additional_code_type": "A",
            "additional_code": "123",
            "ordernumber": "012345",
            "reduction_indicator": "2",
            "validity_start_date": "2021-01-01",
            "validity_end_date": "2022-01-01",
            "measure_generating_regulation_role": "7",
            "measure_generating_regulation_id": "ABCDEF",
            "justification_regulation_role": "8",
            "justification_regulation_id": "GHIJKL",
            "stopped_flag": "1",
            "goods_nomenclature_sid": "123",
            "additional_code_sid": "234",
            "export_refund_nomenclature_sid": "345",
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
        assert target.sid == 1
        assert target.measure_type__sid == "AA"
        assert target.geographical_area__area_id == "BB"
        assert target.geographical_area__sid == 99
        assert target.goods_nomenclature__item_id == "1122334455"
        assert target.goods_nomenclature__sid == 123
        assert target.additional_code__type__sid == "A"
        assert target.additional_code__code == "123"
        assert target.additional_code__sid == 234
        assert target.order_number__order_number == "012345"
        assert target.reduction == 2
        assert target.generating_regulation__role_type == 7
        assert target.generating_regulation__regulation_id == "ABCDEF"
        assert target.terminating_regulation__role_type == 8
        assert target.terminating_regulation__regulation_id == "GHIJKL"
        assert target.stopped is True
        assert target.valid_between_lower == date(2021, 1, 1)
        assert target.valid_between_upper == date(2022, 1, 1)

    def test_import(self, superuser):
        importer = preload_import("measure_CREATE.xml", __file__)

        assert len(importer.parsed_transactions) == 9

        target_message = importer.parsed_transactions[8].parsed_messages[0]
        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target = target_message.taric_object

        assert target.sid == 99
        assert target.measure_type__sid == "ZZZ"
        assert target.geographical_area__area_id == "AB01"
        assert target.geographical_area__sid == 8
        assert target.goods_nomenclature__item_id == "0100000000"
        assert target.goods_nomenclature__sid == 1
        assert target.additional_code__type__sid is None
        assert target.additional_code__code is None
        assert target.additional_code__sid is None
        assert target.order_number__order_number is None
        assert target.reduction is None
        assert target.generating_regulation__role_type == 1
        assert target.generating_regulation__regulation_id == "Z0000001"
        assert target.terminating_regulation__role_type == 1
        assert target.terminating_regulation__regulation_id == "Z0000001"
        assert target.stopped is True
        assert target.valid_between_lower == date(2021, 1, 1)
        assert target.valid_between_upper == date(2022, 1, 1)

        assert len(importer.issues()) == 0

        assert Measure.objects.all().count() == 1

    def test_import_update(self, superuser):
        preload_import("measure_CREATE.xml", __file__, True)
        importer = preload_import("measure_UPDATE.xml", __file__)

        target_message = importer.parsed_transactions[0].parsed_messages[0]

        target = target_message.taric_object

        assert target.sid == 99
        assert target.measure_type__sid == "ZZZ"
        assert target.geographical_area__area_id == "AB01"
        assert target.geographical_area__sid == 8
        assert target.goods_nomenclature__item_id == "0100000000"
        assert target.goods_nomenclature__sid == 1
        assert target.additional_code__type__sid is None
        assert target.additional_code__code is None
        assert target.additional_code__sid is None
        assert target.order_number__order_number is None
        assert target.reduction is None
        assert target.generating_regulation__role_type == 1
        assert target.generating_regulation__regulation_id == "Z0000001"
        assert target.terminating_regulation__role_type == 1
        assert target.terminating_regulation__regulation_id == "Z0000001"
        assert target.stopped is True
        assert target.valid_between_lower == date(2021, 1, 11)
        assert target.valid_between_upper == date(2022, 1, 1)

        assert len(importer.issues()) == 0

        assert Measure.objects.all().count() == 2

    def test_import_delete(self, superuser):
        preload_import("measure_CREATE.xml", __file__, True)
        importer = preload_import("measure_DELETE.xml", __file__)

        assert len(importer.issues()) == 0
        assert importer.can_save()

        assert Measure.objects.all().count() == 2
