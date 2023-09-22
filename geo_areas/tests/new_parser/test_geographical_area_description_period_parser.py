from datetime import date

import pytest

from common.tests import factories

# note : need to import these objects to make them available to the parser
from common.tests.util import get_test_xml_file
from geo_areas.models import GeographicalAreaDescription
from geo_areas.new_import_parsers import NewGeographicalAreaDescriptionPeriodParser
from importer import new_importer
from workbaskets.validators import WorkflowStatus

pytestmark = pytest.mark.django_db


@pytest.mark.new_importer
class TestNewGeographicalAreaDescriptionPeriodParser:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="geographical.area.description.period" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="geographical.area.description.period.sid" type="SID"/>
                    <xs:element name="geographical.area.sid" type="SID"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="geographical.area.id" type="GeographicalAreaId"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    target_parser_class = NewGeographicalAreaDescriptionPeriodParser

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "geographical_area_description_period_sid": "8",
            "geographical_area_sid": "7",
            "validity_start_date": "2021-01-01",
            "geographical_area_id": "6",
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
        assert target.validity_start == date(2021, 1, 1)

    def test_import(self, superuser):
        file_to_import = get_test_xml_file(
            "geographical_area_description_period_CREATE.xml",
            __file__,
        )

        workbasket = factories.WorkBasketFactory.create(status=WorkflowStatus.EDITING)
        import_batch = factories.ImportBatchFactory.create(workbasket=workbasket)

        importer = new_importer.NewImporter(
            import_batch=import_batch,
            taric3_file=file_to_import,
            import_title="Importing stuff",
            author_username=superuser.username,
        )

        assert len(importer.parsed_transactions) == 2

        target_message = importer.parsed_transactions[1].parsed_messages[1]
        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target = target_message.taric_object

        assert target.sid == 3
        assert target.described_geographicalarea__sid == 8
        assert target.described_geographicalarea__area_id == "AB01"
        assert target.validity_start == date(2022, 1, 1)

        assert len(importer.issues()) == 0

        assert GeographicalAreaDescription.objects.all().count() == 1
