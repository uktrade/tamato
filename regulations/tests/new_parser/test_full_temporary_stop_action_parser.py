import pytest

# note : need to import these objects to make them available to the parser
from common.tests.util import preload_import
from regulations.models import Suspension
from regulations.new_import_parsers import NewFullTemporaryStopActionParser

pytestmark = pytest.mark.django_db


@pytest.mark.new_importer
class TestNewFullTemporaryStopActionParser:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="fts.regulation.action" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="fts.regulation.role" type="RegulationRoleTypeId"/>
                    <xs:element name="fts.regulation.id" type="RegulationId"/>
                    <xs:element name="stopped.regulation.role" type="RegulationRoleTypeId"/>
                    <xs:element name="stopped.regulation.id" type="RegulationId"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    target_parser_class = NewFullTemporaryStopActionParser

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "fts_regulation_role": "1",
            "fts_regulation_id": "AB123400",
            "stopped_regulation_role": "3",
            "stopped_regulation_id": "CD567800",
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
        assert target.enacting_regulation__role_type == "1"
        assert target.enacting_regulation__regulation_id == "AB123400"
        assert target.target_regulation__role_type == "3"
        assert target.target_regulation__regulation_id == "CD567800"

    def test_import(self, superuser):
        importer = preload_import("fts_regulation_action_CREATE.xml", __file__)

        assert len(importer.parsed_transactions) == 3

        target_message = importer.parsed_transactions[2].parsed_messages[0]
        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target = target_message.taric_object

        # verify all properties
        assert target.enacting_regulation__role_type == "1"
        assert target.enacting_regulation__regulation_id == "AB123400"
        assert target.target_regulation__role_type == "3"
        assert target.target_regulation__regulation_id == "CD567800"

        assert len(importer.issues()) == 0

        assert Suspension.objects.all().count() == 1
