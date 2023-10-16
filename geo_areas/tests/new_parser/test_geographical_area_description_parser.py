import pytest

# note : need to import these objects to make them available to the parser
from common.tests.util import preload_import
from geo_areas.models import GeographicalAreaDescription
from geo_areas.new_import_parsers import *

pytestmark = pytest.mark.django_db


@pytest.mark.new_importer
class TestNewGeographicalAreaDescriptionParser:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="geographical.area.description" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="geographical.area.description.period.sid" type="SID"/>
                    <xs:element name="language.id" type="LanguageId"/>
                    <xs:element name="geographical.area.sid" type="SID"/>
                    <xs:element name="geographical.area.id" type="GeographicalAreaId"/>
                    <xs:element name="description" type="ShortDescription" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    target_parser_class = NewGeographicalAreaDescriptionParser

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "geographical_area_description_period_sid": "8",
            "language_id": "zz",
            "geographical_area_sid": "7",
            "geographical_area_id": "6",
            "description": "Some Description",
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
        assert target.described_geographicalarea__sid == 7
        assert target.described_geographicalarea__area_id == "6"
        assert target.description == "Some Description"

    def test_import(self, superuser):
        importer = preload_import("geographical_area_description_CREATE.xml", __file__)

        assert len(importer.parsed_transactions) == 2

        target_message = importer.parsed_transactions[1].parsed_messages[0]
        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target = target_message.taric_object

        assert target.sid == 3
        assert target.described_geographicalarea__sid == 8
        assert target.described_geographicalarea__area_id == "AB01"
        assert target.description == "Some Description"

        assert importer.issues() == []

        assert GeographicalAreaDescription.objects.all().count() == 1

    def test_import_update(self, superuser):
        preload_import("geographical_area_description_CREATE.xml", __file__, True)
        importer = preload_import("geographical_area_description_UPDATE.xml", __file__)

        target_message = importer.parsed_transactions[0].parsed_messages[0]
        target = target_message.taric_object

        assert target.sid == 3
        assert target.described_geographicalarea__sid == 8
        assert target.described_geographicalarea__area_id == "AB01"
        assert target.description == "Some Description that changed"

        assert importer.issues() == []

        assert GeographicalAreaDescription.objects.all().count() == 2

    def test_import_delete(self, superuser):
        preload_import("geographical_area_description_CREATE.xml", __file__, True)
        importer = preload_import("geographical_area_description_DELETE.xml", __file__)

        assert importer.issues() == []
        assert importer.can_save()

        assert GeographicalAreaDescription.objects.all().count() == 2
