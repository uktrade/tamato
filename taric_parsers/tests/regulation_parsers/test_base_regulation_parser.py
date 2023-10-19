import pytest

# note : need to import these objects to make them available to the parser
from common.tests.util import preload_import
from regulations.models import Group
from regulations.models import Regulation
from taric_parsers.parsers.additional_code_parsers import *
from taric_parsers.parsers.geo_area_parser import *
from taric_parsers.parsers.regulation_parser import *

pytestmark = pytest.mark.django_db


@pytest.mark.new_importer
class TestNewBaseRegulationParser:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="base.regulation" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="base.regulation.role" type="RegulationRoleTypeId"/>
                    <xs:element name="base.regulation.id" type="RegulationId"/>
                    <xs:element name="published.date" type="Date" minOccurs="0"/>
                    <xs:element name="officialjournal.number" type="OfficialJournalNumber" minOccurs="0"/>
                    <xs:element name="officialjournal.page" type="OfficialJournalPage" minOccurs="0"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                    <xs:element name="effective.end.date" type="Date" minOccurs="0"/>
                    <xs:element name="community.code" type="CommunityCode"/>
                    <xs:element name="regulation.group.id" type="RegulationGroupId"/>
                    <xs:element name="antidumping.regulation.role" type="RegulationRoleTypeId" minOccurs="0"/>
                    <xs:element name="related.antidumping.regulation.id" type="RegulationId" minOccurs="0"/>
                    <xs:element name="complete.abrogation.regulation.role" type="RegulationRoleTypeId" minOccurs="0"/>
                    <xs:element name="complete.abrogation.regulation.id" type="RegulationId" minOccurs="0"/>
                    <xs:element name="explicit.abrogation.regulation.role" type="RegulationRoleTypeId" minOccurs="0"/>
                    <xs:element name="explicit.abrogation.regulation.id" type="RegulationId" minOccurs="0"/>
                    <xs:element name="replacement.indicator" type="ReplacementIndicator"/>
                    <xs:element name="stopped.flag" type="StoppedFlag"/>
                    <xs:element name="information.text" type="ShortDescription" minOccurs="0"/>
                    <xs:element name="approved.flag" type="ApprovedFlag"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    target_parser_class = NewBaseRegulationParser

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "base_regulation_role": "1",
            "base_regulation_id": "Z0000001",
            "published_date": "2023-01-01",
            "officialjournal_number": "ABCDE",
            "officialjournal_page": "7",
            "validity_start_date": "2021-01-01",
            "validity_end_date": "2022-01-01",
            "effective_end_date": "2023-01-01",
            "community_code": "1",
            "regulation_group_id": "ABC",
            "replacement_indicator": "7",
            "stopped_flag": "0",
            "information_text": "Some Info Text",
            "approved_flag": "1",
            "antidumping_regulation_role": "1",
            "related_antidumping_regulation_id": "A00000001",
            "complete_abrogation_regulation_role": "1",
            "complete_abrogation_regulation_id": "B00000001",
            "explicit_abrogation_regulation_role": "1",
            "explicit_abrogation_regulation_id": "C00000001",
        }

        target = self.target_parser_class()

        target.populate(
            1,  # transaction id
            target.record_code,
            target.subrecord_code,
            1,  # sequence number
            expected_data_example,
        )

        assert target.role_type == 1
        assert target.regulation_id == "Z0000001"
        assert target.published_at == date(2023, 1, 1)
        assert target.official_journal_number == "ABCDE"
        assert target.official_journal_page == 7
        assert target.valid_between_lower == date(2021, 1, 1)
        assert target.valid_between_upper == date(2022, 1, 1)
        assert target.effective_end_date == date(2023, 1, 1)
        assert target.community_code == 1
        assert target.regulation_group__group_id == "ABC"
        assert target.replacement_indicator == 7
        assert target.stopped is False
        assert target.information_text == "Some Info Text"
        assert target.approved is True

    def test_import(self, superuser):
        importer = preload_import(
            "base_regulation_CREATE.xml",
            __file__,
        )

        assert len(importer.parsed_transactions) == 2

        target_message = importer.parsed_transactions[1].parsed_messages[0]
        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target = target_message.taric_object

        # verify all properties
        assert target.role_type == 1
        assert target.regulation_id == "Z0000001"
        assert target.published_at == date(2023, 1, 1)
        assert target.official_journal_number == "ABCDE"
        assert target.official_journal_page == 7
        assert target.valid_between_lower == date(2021, 1, 1)
        assert target.valid_between_upper == date(2022, 1, 1)
        assert target.effective_end_date == date(2023, 1, 1)
        assert target.community_code == 1
        assert target.regulation_group__group_id == "ABC"
        assert target.replacement_indicator == 7
        assert target.stopped is False
        assert target.information_text == "Some Info Text"
        assert target.approved is True

        assert len(importer.issues()) == 0

        assert Group.objects.all().count() == 1

    def test_import_update(self, superuser):
        preload_import(
            "base_regulation_CREATE.xml",
            __file__,
            True,
        )
        importer = preload_import(
            "base_regulation_UPDATE.xml",
            __file__,
        )

        target_message = importer.parsed_transactions[0].parsed_messages[0]
        target = target_message.taric_object

        # verify all properties
        assert target.role_type == 1
        assert target.regulation_id == "Z0000001"
        assert target.published_at == date(2023, 1, 11)
        assert target.official_journal_number == "ABCDE"
        assert target.official_journal_page == 7
        assert target.valid_between_lower == date(2021, 1, 11)
        assert target.valid_between_upper == date(2022, 1, 11)
        assert target.effective_end_date == date(2023, 1, 11)
        assert target.community_code == 1
        assert target.regulation_group__group_id == "ABC"
        assert target.replacement_indicator == 7
        assert target.stopped is False
        assert target.information_text == "Some Info Text with changes"
        assert target.approved is True

        assert len(importer.issues()) == 0

        assert Regulation.objects.all().count() == 2
