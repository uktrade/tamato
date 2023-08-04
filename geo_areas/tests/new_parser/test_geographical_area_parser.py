from datetime import date

import pytest

# note : need to import these objects to make them available to the parser
from common.tests.util import get_test_xml_file
from footnotes.models import FootnoteDescription
from geo_areas.new_import_parsers import NewGeographicalAreaParser
from importer import new_importer

pytestmark = pytest.mark.django_db


@pytest.mark.new_importer
class TestNewGeographicalAreaParser:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="geographical.area" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="geographical.area.sid" type="SID"/>
                    <xs:element name="geographical.area.id" type="GeographicalAreaId"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                    <xs:element name="geographical.code" type="AreaCode"/>
                    <xs:element name="parent.geographical.area.group.sid" type="SID" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    target_parser_class = NewGeographicalAreaParser

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "geographical_area_sid": "8",
            "geographical_area_id": "9",
            "validity_start_date": "2021-01-01",
            "validity_end_date": "2022-01-01",
            "geographical_code": "5",
            "parent_geographical_area_group_sid": "7",
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

        assert target.sid == 8
        assert target.area_id == "9"
        assert target.valid_between_lower == date(2021, 1, 1)
        assert target.valid_between_upper == date(2022, 1, 1)
        assert target.area_code == "5"
        assert target.parent__sid == 7

        assert target.sid == 8
        assert target.described_footnote__footnote_type__footnote_type_id == "7"
        assert target.described_footnote__footnote_id == "6"
        assert target.description == "Some Description"

    def test_import(self, superuser):
        file_to_import = get_test_xml_file("geographical_area_CREATE.xml", __file__)

        importer = new_importer.NewImporter(
            file_to_import,
            import_title="Importing stuff",
            author_username=superuser.username,
        )

        # check there is one AdditionalCodeType imported
        assert len(importer.parsed_transactions) == 2

        target_message = importer.parsed_transactions[1].parsed_messages[0]
        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        # check properties for additional code
        target = target_message.taric_object

        assert target.sid == 7
        assert target.described_footnote__footnote_type__footnote_type_id == "3"
        assert target.described_footnote__footnote_id == "9"
        assert target.description == "Some Description"

        assert len(importer.issues()) == 0

        assert FootnoteDescription.objects.all().count() == 1
