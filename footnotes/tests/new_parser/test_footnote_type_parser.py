from datetime import date

import pytest

# note : need to import these objects to make them available to the parser
from common.tests.util import preload_import
from footnotes.models import FootnoteType
from footnotes.new_import_parsers import NewFootnoteTypeParser

pytestmark = pytest.mark.django_db


@pytest.mark.new_importer
class TestNewFootnoteTypeParser:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="footnote.type" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="footnote.type.id" type="FootnoteTypeId"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                    <xs:element name="application.code" type="ApplicationCodeFootnote"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    target_parser_class = NewFootnoteTypeParser

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "footnote_type_id": "4",
            "validity_start_date": "2021-01-01",
            "validity_end_date": "2022-01-01",
            "application_code": "7",
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
        assert target.footnote_type_id == "4"
        assert target.valid_between_lower == date(2021, 1, 1)
        assert target.valid_between_upper == date(2022, 1, 1)
        assert target.application_code == "7"

    def test_import(self, superuser):
        importer = preload_import("footnote_type_CREATE.xml", __file__)

        assert len(importer.parsed_transactions) == 1

        target_message = importer.parsed_transactions[0].parsed_messages[1]

        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target_taric_object = target_message.taric_object

        assert target_taric_object.footnote_type_id == "3"
        assert target_taric_object.valid_between_lower == date(2021, 1, 1)
        assert target_taric_object.valid_between_upper == date(2021, 12, 1)
        assert target_taric_object.application_code == "9"

        assert FootnoteType.objects.all().count() == 1

        assert len(importer.issues()) == 0

    def test_import_update(self, superuser):
        preload_import("footnote_type_CREATE.xml", __file__, True)
        importer = preload_import("footnote_type_UPDATE.xml", __file__)

        target_message = importer.parsed_transactions[0].parsed_messages[0]

        target_taric_object = target_message.taric_object

        assert target_taric_object.footnote_type_id == "3"
        assert target_taric_object.valid_between_lower == date(2021, 1, 1)
        assert target_taric_object.valid_between_upper == date(2021, 12, 22)
        assert target_taric_object.application_code == "9"

        assert importer.issues() == []
        assert FootnoteType.objects.all().count() == 2

    def test_import_delete(self, superuser):
        preload_import("footnote_type_CREATE.xml", __file__, True)
        importer = preload_import("footnote_type_DELETE.xml", __file__)

        assert importer.issues() == []
        assert importer.can_save()
        assert FootnoteType.objects.all().count() == 2

    def test_import_no_description(self, superuser):
        importer = preload_import("footnote_type_no_description_CREATE.xml", __file__)

        assert len(importer.parsed_transactions) == 1
        assert len(importer.parsed_transactions[0].parsed_messages) == 1

        assert FootnoteType.objects.all().count() == 0

        assert len(importer.issues()) == 1
