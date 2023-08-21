import pytest

# note : need to import these objects to make them available to the parser
from common.tests.util import get_test_xml_file
from importer import new_importer
from regulations.models import Group
from regulations.new_import_parsers import NewRegulationGroupDescriptionParser

pytestmark = pytest.mark.django_db


@pytest.mark.new_importer
class TestNewRegulationGroupDescriptionParser:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="regulation.group.description" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="regulation.group.id" type="RegulationGroupId"/>
                    <xs:element name="language.id" type="LanguageId"/>
                    <xs:element name="description" type="ShortDescription" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    target_parser_class = NewRegulationGroupDescriptionParser

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "regulation_group_id": "ASD",
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
        assert target.group_id == "ASD"
        assert target.description == "Some Description"

    def test_import(self, superuser):
        file_to_import = get_test_xml_file(
            "regulation_group_description_CREATE.xml",
            __file__,
        )

        importer = new_importer.NewImporter(
            file_to_import,
            import_title="Importing stuff",
            author_username=superuser.username,
        )

        # check there is one AdditionalCodeType imported
        assert len(importer.parsed_transactions) == 1

        target_message = importer.parsed_transactions[0].parsed_messages[1]
        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        # check properties for additional code
        target = target_message.taric_object

        # verify all properties
        assert target.group_id == "ABC"
        assert target.description == "Some Description x"

        assert len(importer.issues()) == 0

        assert Group.objects.all().count() == 1
