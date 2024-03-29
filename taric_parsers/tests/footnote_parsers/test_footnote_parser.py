from datetime import date

import pytest

# note : need to import these objects to make them available to the parser
from common.tests.util import preload_import
from footnotes.models import Footnote
from taric_parsers.parsers.footnote_parser import *

pytestmark = pytest.mark.django_db


@pytest.mark.importer_v2
class TestFootnoteParserV2:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="footnote" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="footnote.type.id" type="FootnoteTypeId"/>
                    <xs:element name="footnote.id" type="FootnoteId"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    target_parser_class = FootnoteParserV2

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "footnote_type_id": "7",
            "footnote_id": "6",
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
        assert target.footnote_type__footnote_type_id == "7"
        assert target.footnote_id == "6"
        assert target.valid_between_lower == date(2021, 1, 1)
        assert target.valid_between_upper == date(2022, 1, 1)

    def test_import(self, superuser):
        importer = preload_import("footnote_CREATE.xml", __file__)

        assert len(importer.parsed_transactions) == 1

        target_message = importer.parsed_transactions[0].parsed_messages[3]

        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target = target_message.taric_object
        assert target.footnote_type__footnote_type_id == "3"
        assert target.footnote_id == "9"
        assert target.valid_between_lower == date(2021, 1, 1)
        assert target.valid_between_upper == date(2021, 1, 1)

        assert Footnote.objects.all().count() == 1

        assert len(importer.issues()) == 0

    def test_import_update(self, superuser):
        preload_import("footnote_CREATE.xml", __file__, True)
        importer = preload_import("footnote_UPDATE.xml", __file__)

        target_message = importer.parsed_transactions[0].parsed_messages[0]

        target = target_message.taric_object

        assert target.footnote_type__footnote_type_id == "3"
        assert target.footnote_id == "9"
        assert target.valid_between_lower == date(2021, 1, 1)
        assert target.valid_between_upper == date(2021, 1, 22)

        assert Footnote.objects.all().count() == 2

        assert importer.issues() == []

    def test_import_delete(self, superuser):
        preload_import("footnote_CREATE.xml", __file__, True)
        importer = preload_import("footnote_DELETE.xml", __file__)

        assert importer.issues() == []
        assert importer.can_save()

        assert Footnote.objects.all().count() == 2
