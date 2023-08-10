import pytest

# note : need to import these objects to make them available to the parser
from common.tests.util import get_test_xml_file
from geo_areas.new_import_parsers import *
from importer import new_importer
from measures.new_import_parsers import NewMeasureTypeSeriesParser

pytestmark = pytest.mark.django_db


@pytest.mark.new_importer
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
        file_to_import = get_test_xml_file(
            "measure_series_CREATE.xml",
            __file__,
        )

        importer = new_importer.NewImporter(
            file_to_import,
            import_title="Importing stuff",
            author_username=superuser.username,
        )

        # check there is one AdditionalCodeType imported
        assert len(importer.parsed_transactions) == 1

        target_message = importer.parsed_transactions[0].parsed_messages[0]
        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        # check properties for additional code
        target = target_message.taric_object

        assert target.sid == "A"
        assert target.valid_between_lower == date(2021, 1, 1)
        assert target.valid_between_upper == date(2022, 1, 1)
        assert target.measure_type_combination == 6

        assert len(importer.issues()) == 0

        assert MeasureTypeSereise.objects.all().count() == 1
