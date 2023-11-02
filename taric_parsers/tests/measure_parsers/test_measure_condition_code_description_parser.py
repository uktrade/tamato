import pytest

# note : need to import these objects to make them available to the parser
from common.tests.util import preload_import
from measures.models import MeasureConditionCode
from taric_parsers.parsers.measure_parser import *

pytestmark = pytest.mark.django_db


@pytest.mark.new_importer
class TestNewMeasureConditionCodeDescriptionParser:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="measure.condition.code.description" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="condition.code" type="ConditionCode"/>
                    <xs:element name="language.id" type="LanguageId"/>
                    <xs:element name="description" type="ShortDescription" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    target_parser_class = NewMeasureConditionCodeDescriptionParser

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "condition_code": "A",
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
        assert target.code == "A"
        assert target.description == "Some Description"

    def test_import(self, superuser):
        importer = preload_import(
            "measure_condition_code_description_CREATE.xml",
            __file__,
        )

        assert len(importer.parsed_transactions) == 1

        target_message = importer.parsed_transactions[0].parsed_messages[1]
        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target = target_message.taric_object

        # verify all properties
        assert target.code == "A"
        assert target.description == "Some Description"

        assert len(importer.issues()) == 0

        assert MeasureConditionCode.objects.all().count() == 1

    def test_import_update(self, superuser):
        preload_import("measure_condition_code_description_CREATE.xml", __file__, True)
        importer = preload_import(
            "measure_condition_code_description_UPDATE.xml",
            __file__,
        )

        target_message = importer.parsed_transactions[0].parsed_messages[0]
        target = target_message.taric_object

        # verify all properties
        assert target.code == "A"
        assert target.description == "Some Description with changes"

        assert len(importer.issues()) == 0

        assert MeasureConditionCode.objects.all().count() == 2

    def test_import_delete(self, superuser):
        preload_import("measure_condition_code_description_CREATE.xml", __file__, True)
        importer = preload_import(
            "measure_condition_code_description_DELETE.xml",
            __file__,
        )

        assert importer.can_save()

        assert len(importer.issues()) == 1

        assert (
            "Children of Taric objects of type MeasureConditionCode can't be deleted directly"
            in str(importer.issues()[0])
        )
