import pytest

from common.tests import factories

# note : need to import these objects to make them available to the parser
from common.tests.util import get_test_xml_file
from geo_areas.new_import_parsers import *
from importer import new_importer
from measures.models import Measurement
from measures.new_import_parsers import NewMeasurementParser
from workbaskets.validators import WorkflowStatus

pytestmark = pytest.mark.django_db


@pytest.mark.new_importer
class TestNewMeasurementParser:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="measurement" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="measurement.unit.code" type="MeasurementUnitCode"/>
                    <xs:element name="measurement.unit.qualifier.code" type="MeasurementUnitQualifierCode"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    target_parser_class = NewMeasurementParser

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "measurement_unit_code": "ABC",
            "measurement_unit_qualifier_code": "D",
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
        assert target.measurement_unit__code == "ABC"
        assert target.measurement_unit_qualifier__code == "D"
        assert target.valid_between_lower == date(2021, 1, 1)
        assert target.valid_between_upper == date(2022, 1, 1)

    def test_import(self, superuser):
        file_to_import = get_test_xml_file(
            "measurement_CREATE.xml",
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

        assert len(importer.parsed_transactions) == 3

        target_message = importer.parsed_transactions[2].parsed_messages[0]
        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target = target_message.taric_object

        assert target.measurement_unit__code == "XXX"
        assert target.measurement_unit_qualifier__code == "A"
        assert target.valid_between_lower == date(2021, 1, 1)
        assert target.valid_between_upper == date(2022, 1, 1)

        assert len(importer.issues()) == 0

        assert Measurement.objects.all().count() == 1
