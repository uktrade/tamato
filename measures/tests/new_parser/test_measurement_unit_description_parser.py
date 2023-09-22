import pytest

from common.tests import factories

# note : need to import these objects to make them available to the parser
from common.tests.util import get_test_xml_file
from importer import new_importer
from measures.models import MeasurementUnit
from measures.new_import_parsers import NewMeasurementUnitDescriptionParser
from workbaskets.validators import WorkflowStatus

pytestmark = pytest.mark.django_db


@pytest.mark.new_importer
class TestNewMeasurementUnitDescriptionParser:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="measurement.unit.description" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="measurement.unit.code" type="MeasurementUnitCode"/>
                    <xs:element name="language.id" type="LanguageId"/>
                    <xs:element name="description" type="ShortDescription" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    target_parser_class = NewMeasurementUnitDescriptionParser

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "measurement_unit_code": "XXX",
            "language_id": "ZZ",
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
        assert target.code == "XXX"
        assert target.description == "Some Description"

    def test_import(self, superuser):
        file_to_import = get_test_xml_file(
            "measurement_unit_description_CREATE.xml",
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

        assert len(importer.parsed_transactions) == 1

        target_message = importer.parsed_transactions[0].parsed_messages[1]
        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target = target_message.taric_object

        assert target.code == "XXX"
        assert target.description == "Some Description"

        assert len(importer.issues()) == 0

        assert MeasurementUnit.objects.all().count() == 1
