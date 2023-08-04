import pytest

# note : need to import these objects to make them available to the parser
from common.tests.util import get_test_xml_file
from footnotes.models import FootnoteType
from footnotes.new_import_parsers import NewFootnoteTypeDescriptionParser
from importer import new_importer

pytestmark = pytest.mark.django_db


@pytest.mark.new_importer
class TestNewFootnoteTypeDescriptionParser:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="footnote.type.description" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="footnote.type.id" type="FootnoteTypeId"/>
                    <xs:element name="language.id" type="LanguageId"/>
                    <xs:element name="description" type="ShortDescription" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    target_parser_class = NewFootnoteTypeDescriptionParser

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "footnote_type_id": "3",
            "language_id": "zz",  # gets ignored, but will come in from import
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
        assert target.footnote_type_id == "3"
        assert target.description == "Some Description"

    def test_import(self, superuser):
        file_to_import = get_test_xml_file(
            "footnote_type_description_CREATE.xml",
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
        assert target.footnote_type_id == "3"
        assert target.description == "Some description"

        assert FootnoteType.objects.all().count() == 1
        assert len(importer.issues()) == 0
