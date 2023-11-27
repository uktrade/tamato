import pytest

# note : need to import these objects to make them available to the parser
from common.tests.util import preload_import
from regulations.models import Replacement
from taric_parsers.parsers.additional_code_parsers import *
from taric_parsers.parsers.geo_area_parser import *
from taric_parsers.parsers.measure_parser import *
from taric_parsers.parsers.regulation_parser import *

pytestmark = pytest.mark.django_db


@pytest.mark.importer_v2
class TestNewRegulationReplacementParser:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="regulation.replacement" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="replacing.regulation.role" type="RegulationRoleTypeId"/>
                    <xs:element name="replacing.regulation.id" type="RegulationId"/>
                    <xs:element name="replaced.regulation.role" type="RegulationRoleTypeId"/>
                    <xs:element name="replaced.regulation.id" type="RegulationId"/>
                    <xs:element name="measure.type.id" type="MeasureTypeId" minOccurs="0"/>
                    <xs:element name="geographical.area.id" type="GeographicalAreaId" minOccurs="0"/>
                    <xs:element name="chapter.heading" type="ChapterHeading" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    target_parser_class = NewRegulationReplacementParser

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "replacing_regulation_role": "3",
            "replacing_regulation_id": "AB123123",
            "replaced_regulation_role": "1",
            "replaced_regulation_id": "CD123123",
            "measure_type_id": "ABC1",
            "geographical_area_id": "AB12",
            "chapter_heading": "09",
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
        assert target.enacting_regulation__role_type == 3
        assert target.enacting_regulation__regulation_id == "AB123123"
        assert target.target_regulation__role_type == 1
        assert target.target_regulation__regulation_id == "CD123123"
        assert target.measure_type_id == "ABC1"
        assert target.geographical_area_id == "AB12"
        assert target.chapter_heading == "09"

    def test_import(self, superuser):
        importer = preload_import(
            "regulation_replacement_CREATE.xml",
            __file__,
        )

        assert len(importer.parsed_transactions) == 6

        target_message = importer.parsed_transactions[5].parsed_messages[0]
        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target = target_message.taric_object

        # verify all properties
        assert target.enacting_regulation__role_type == 1
        assert target.enacting_regulation__regulation_id == "Z0000001"
        assert target.target_regulation__role_type == 3
        assert target.target_regulation__regulation_id == "Z0000002"
        assert target.measure_type_id == "ZZZ"
        assert target.geographical_area_id == "AB01"
        assert target.chapter_heading == "09"

        assert len(importer.issues()) == 0

        assert Replacement.objects.all().count() == 1
