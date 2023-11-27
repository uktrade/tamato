import pytest

# note : need to import these objects to make them available to the parser
from common.tests.util import preload_import
from measures.models import MeasureTypeSeries
from taric_parsers.parsers.geo_area_parser import *
from taric_parsers.parsers.measure_parser import *

pytestmark = pytest.mark.django_db


@pytest.mark.importer_v2
class TestNewMeasureTypeSeriesParser:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="measure.type.series" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="measure.type.series.id" type="MeasureTypeSeriesId"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                    <xs:element name="measure.type.combination" type="MeasureTypeCombination"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    target_parser_class = NewMeasureTypeSeriesParser

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "measure_type_series_id": "A",
            "validity_start_date": "2021-01-01",
            "validity_end_date": "2022-01-01",
            "measure_type_combination": "6",
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
        assert target.sid == "A"
        assert target.valid_between_lower == date(2021, 1, 1)
        assert target.valid_between_upper == date(2022, 1, 1)
        assert target.measure_type_combination == 6

    def test_import(self, superuser):
        importer = preload_import("measure_series_CREATE.xml", __file__)

        assert len(importer.parsed_transactions) == 1

        target_message = importer.parsed_transactions[0].parsed_messages[0]
        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target = target_message.taric_object

        assert target.sid == "A"
        assert target.valid_between_lower == date(2021, 1, 1)
        assert target.valid_between_upper == date(2022, 1, 1)
        assert target.measure_type_combination == 6

        assert len(importer.issues()) == 0

        assert MeasureTypeSeries.objects.all().count() == 1

    def test_import_update(self, superuser):
        preload_import("measure_series_CREATE.xml", __file__, True)
        importer = preload_import("measure_series_UPDATE.xml", __file__)

        target_message = importer.parsed_transactions[0].parsed_messages[0]

        target = target_message.taric_object

        assert target.sid == "A"
        assert target.valid_between_lower == date(2021, 1, 11)
        assert target.valid_between_upper == date(2022, 1, 1)
        assert target.measure_type_combination == 6

        assert len(importer.issues()) == 0

        assert MeasureTypeSeries.objects.all().count() == 2

    def test_import_delete(self, superuser):
        preload_import("measure_series_CREATE.xml", __file__, True)
        importer = preload_import("measure_series_DELETE.xml", __file__)

        assert importer.issues() == []
        assert importer.can_save()

        assert MeasureTypeSeries.objects.all().count() == 2

    def test_import_failure_no_description(self, superuser):
        importer = preload_import("measure_series_no_description_CREATE.xml", __file__)

        assert len(importer.parsed_transactions) == 1

        target_message = importer.parsed_transactions[0].parsed_messages[0]
        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target = target_message.taric_object

        assert target.sid == "A"
        assert target.valid_between_lower == date(2021, 1, 1)
        assert target.valid_between_upper == date(2022, 1, 1)
        assert target.measure_type_combination == 6

        assert len(importer.issues()) == 1

        issue_error_str = str(importer.issues()[0])

        assert (
            "ERROR: Missing expected child object NewMeasureTypeSeriesDescriptionParser"
            in issue_error_str
        )
        assert (
            "measure.type.series > measure.type.series.description" in issue_error_str
        )

        assert importer.can_save() is False
