from datetime import date

import pytest

# note : need to import these objects to make them available to the parser
from common.tests.util import get_test_xml_file
from footnotes.models import FootnoteDescription
from footnotes.new_import_parsers import NewFootnoteDescriptionPeriodParser
from importer import new_importer

pytestmark = pytest.mark.django_db


@pytest.mark.new_importer
class TestNewFootnoteDescriptionPeriodParser:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="footnote.description.period" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="footnote.description.period.sid" type="SID"/>
                    <xs:element name="footnote.type.id" type="FootnoteTypeId"/>
                    <xs:element name="footnote.id" type="FootnoteId"/>
                    <xs:element name="validity.start.date" type="Date"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    target_parser_class = NewFootnoteDescriptionPeriodParser

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "footnote_description_period_sid": "8",
            "footnote_type_id": "7",
            "footnote_id": "6",
            "validity_start_date": "2022-01-01",
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
        assert target.sid == 8
        assert target.described_footnote__footnote_type__footnote_type_id == "7"
        assert target.described_footnote__footnote_id == "6"
        assert target.validity_start == date(2022, 1, 1)

    def test_import(self, superuser):
        file_to_import = get_test_xml_file(
            "footnote_description_period_CREATE.xml",
            __file__,
        )

        importer = new_importer.NewImporter(
            file_to_import,
            import_title="Importing stuff",
            author_username=superuser.username,
        )

        # check there is one AdditionalCodeType imported
        assert len(importer.parsed_transactions) == 2

        target_message = importer.parsed_transactions[1].parsed_messages[1]

        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        # check properties for additional code
        target = target_message.taric_object

        assert target.sid == 7
        assert target.described_footnote__footnote_type__footnote_type_id == "3"
        assert target.described_footnote__footnote_id == "9"
        assert target.validity_start == date(2021, 1, 1)

        assert len(importer.issues()) == 0

        assert FootnoteDescription.objects.all().count() == 1
