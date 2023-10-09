import pytest

# note : need to import these objects to make them available to the parser
from common.tests.util import preload_import
from measures.models import MeasureType
from measures.new_import_parsers import NewMeasureTypeDescriptionParser

pytestmark = pytest.mark.django_db


@pytest.mark.new_importer
class TestNewMeasureTypeDescriptionParser:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="measure.type.description" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="measure.type.id" type="MeasureTypeId"/>
                    <xs:element name="language.id" type="LanguageId"/>
                    <xs:element name="description" type="ShortDescription" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    target_parser_class = NewMeasureTypeDescriptionParser

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "measure_type_id": "AAA",
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
        assert target.sid == "AAA"
        assert target.description == "Some Description"

    def test_import(self, superuser):
        importer = preload_import("measure_type_description_CREATE.xml", __file__)

        assert len(importer.parsed_transactions) == 2

        target_message = importer.parsed_transactions[1].parsed_messages[1]
        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target = target_message.taric_object

        assert target.sid == "ZZZ"
        assert target.description == "Some Description x"

        assert len(importer.issues()) == 0

        assert MeasureType.objects.all().count() == 1
