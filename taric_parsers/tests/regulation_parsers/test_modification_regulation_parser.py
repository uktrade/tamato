import pytest

# note : need to import these objects to make them available to the parser
from taric_parsers.parsers.additional_code_parsers import *
from taric_parsers.parsers.geo_area_parser import *
from taric_parsers.parsers.regulation_parser import *

pytestmark = pytest.mark.django_db


@pytest.mark.new_importer
class TestNewModificationRegulationParser:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="modification.regulation" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="modification.regulation.role" type="RegulationRoleTypeId"/>
                    <xs:element name="modification.regulation.id" type="RegulationId"/>
                    <xs:element name="published.date" type="Date" minOccurs="0"/>
                    <xs:element name="officialjournal.number" type="OfficialJournalNumber" minOccurs="0"/>
                    <xs:element name="officialjournal.page" type="OfficialJournalPage" minOccurs="0"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                    <xs:element name="effective.end.date" type="Date" minOccurs="0"/>
                    <xs:element name="base.regulation.role" type="RegulationRoleTypeId"/>
                    <xs:element name="base.regulation.id" type="RegulationId"/>
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

        "modification_regulation_role":"",
        "modification_regulation_id":"",
        "published_date" type="Date":"",
        "officialjournal_number":"",
        "officialjournal_page":"",
        "validity_start_date":"",
        "validity_end_date":"",
        "effective_end_date":"",
        "base_regulation_role":"",
        "base_regulation_id":"",
        "complete_abrogation_regulation_role":"",
        "complete_abrogation_regulation_id":"",
        "explicit_abrogation_regulation_role":"",
        "explicit_abrogation_regulation_id":"",
        "replacement_indicator":"",
        "stopped_flag":"",
        "information_text":"",
        "approved_flag":"",
    """

    target_parser_class = NewModificationRegulationParser

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "modification_regulation_role": "3",
            "modification_regulation_id": "AB123123",
            "published_date": "2022-01-01",
            "officialjournal_number": "AB123",
            "officialjournal_page": "77",
            "validity_start_date": "2022-01-01",
            "validity_end_date": "2023-01-01",
            "effective_end_date": "2021-01-01",
            "base_regulation_role": "1",
            "base_regulation_id": "CD123123",
            "complete_abrogation_regulation_role": "3",
            "complete_abrogation_regulation_id": "EF123123",
            "explicit_abrogation_regulation_role": "3",
            "explicit_abrogation_regulation_id": "GH123123",
            "replacement_indicator": "0",
            "stopped_flag": "0",
            "information_text": "info text",
            "approved_flag": "1",
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
        assert target.enacting_regulation__role_type == 3
        assert target.enacting_regulation__regulation_id == "AB123123"
        assert target.enacting_regulation__published_at == date(2022, 1, 1)
        assert target.enacting_regulation__official_journal_number == "AB123"
        assert target.enacting_regulation__official_journal_page == 77
        assert target.enacting_regulation__valid_between_lower == date(2022, 1, 1)
        assert target.enacting_regulation__valid_between_upper == date(2023, 1, 1)
        assert target.enacting_regulation__effective_end_date == date(2021, 1, 1)
        assert target.target_regulation__role_type == 1
        assert target.target_regulation__regulation_id == "CD123123"
        assert target.enacting_regulation__replacement_indicator == 0
        assert target.enacting_regulation__stopped is False
        assert target.enacting_regulation__information_text == "info text"
        assert target.enacting_regulation__approved is True
