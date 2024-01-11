import pytest

# note : need to import these objects to make them available to the parser
from common.tests.util import preload_import
from measures.models import MeasureExcludedGeographicalArea
from taric_parsers.parsers.measure_parser import *

pytestmark = pytest.mark.django_db


@pytest.mark.importer_v2
class TestMeasureExcludedGeographicalAreaParserV2:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="measure.excluded.geographical.area" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="measure.sid" type="SID"/>
                    <xs:element name="excluded.geographical.area" type="GeographicalAreaId"/>
                    <xs:element name="geographical.area.sid" type="SID"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    target_parser_class = MeasureExcludedGeographicalAreaParserV2

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "measure_sid": "12",
            "excluded_geographical_area": "ABCD",
            "geographical_area_sid": "77",
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
        assert target.modified_measure__sid == 12
        assert target.excluded_geographical_area__area_id == "ABCD"
        assert target.excluded_geographical_area__sid == 77

    def test_import(self, superuser):
        importer = preload_import(
            "measure_excluded_geographical_area_CREATE.xml",
            __file__,
        )

        assert len(importer.parsed_transactions) == 10

        target_message = importer.parsed_transactions[9].parsed_messages[0]
        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target = target_message.taric_object

        assert target.modified_measure__sid == 99
        assert target.excluded_geographical_area__area_id == "AB01"
        assert target.excluded_geographical_area__sid == 8

        assert len(importer.issues()) == 0

        assert MeasureExcludedGeographicalArea.objects.all().count() == 1

    def test_import_update(self, superuser):
        preload_import("measure_excluded_geographical_area_CREATE.xml", __file__, True)
        importer = preload_import(
            "measure_excluded_geographical_area_UPDATE.xml",
            __file__,
        )

        target_message = importer.parsed_transactions[0].parsed_messages[0]

        target = target_message.taric_object

        assert target.modified_measure__sid == 99
        assert target.excluded_geographical_area__area_id == "AB01"
        assert target.excluded_geographical_area__sid == 8

        assert len(importer.issues()) == 0

        assert MeasureExcludedGeographicalArea.objects.all().count() == 2

    def test_import_delete(self, superuser):
        preload_import("measure_excluded_geographical_area_CREATE.xml", __file__, True)
        importer = preload_import(
            "measure_excluded_geographical_area_DELETE.xml",
            __file__,
        )

        assert len(importer.issues()) == 0
        assert importer.can_save()

        assert MeasureExcludedGeographicalArea.objects.all().count() == 2
