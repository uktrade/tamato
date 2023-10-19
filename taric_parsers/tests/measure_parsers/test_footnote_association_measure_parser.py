import pytest

# note : need to import these objects to make them available to the parser
from common.tests.util import preload_import
from measures.models import FootnoteAssociationMeasure
from taric_parsers.parsers.measure_parser import *

pytestmark = pytest.mark.django_db


@pytest.mark.new_importer
class TestNewFootnoteAssociationMeasureParser:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="footnote.association.measure" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="measure.sid" type="SID"/>
                    <xs:element name="footnote.type.id" type="FootnoteTypeId"/>
                    <xs:element name="footnote.id" type="FootnoteId"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    target_parser_class = NewFootnoteAssociationMeasureParser

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "measure_sid": "1",
            "footnote_type_id": "AA",
            "footnote_id": "BBB",
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
        assert target.footnoted_measure__sid == 1
        assert target.associated_footnote__footnote_type__footnote_type_id == "AA"
        assert target.associated_footnote__footnote_id == "BBB"

    def test_import(self, superuser):
        importer = preload_import("footnote_association_measure_CREATE.xml", __file__)

        assert len(importer.parsed_transactions) == 11

        target_message = importer.parsed_transactions[10].parsed_messages[0]
        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target = target_message.taric_object

        assert target.footnoted_measure__sid == 99
        assert target.associated_footnote__footnote_type__footnote_type_id == "3"
        assert target.associated_footnote__footnote_id == "9"

        assert len(importer.issues()) == 0

        assert FootnoteAssociationMeasure.objects.all().count() == 1

    def test_import_update_raises_issue(self, superuser):
        preload_import("footnote_association_measure_CREATE.xml", __file__, True)
        importer = preload_import("footnote_association_measure_UPDATE.xml", __file__)

        assert len(importer.issues()) == 1

        assert (
            "Taric objects of type FootnoteAssociationMeasure can't be updated"
            in str(importer.issues()[0])
        )

    def test_import_delete(self, superuser):
        preload_import("footnote_association_measure_CREATE.xml", __file__, True)
        importer = preload_import("footnote_association_measure_DELETE.xml", __file__)

        assert len(importer.issues()) == 0
        assert importer.can_save()

        assert FootnoteAssociationMeasure.objects.all().count() == 2
