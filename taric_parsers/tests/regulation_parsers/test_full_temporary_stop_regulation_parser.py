import pytest

# note : need to import these objects to make them available to the parser
from taric_parsers.parsers.additional_code_parsers import *
from taric_parsers.parsers.geo_area_parser import *
from taric_parsers.parsers.regulation_parser import *

pytestmark = pytest.mark.django_db


@pytest.mark.importer_v2
class TestFullTemporaryStopRegulationParserV2:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="full.temporary.stop.regulation" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="full.temporary.stop.regulation.role" type="RegulationRoleTypeId"/>
                    <xs:element name="full.temporary.stop.regulation.id" type="RegulationId"/>
                    <xs:element name="published.date" type="Date" minOccurs="0"/>
                    <xs:element name="officialjournal.number" type="OfficialJournalNumber" minOccurs="0"/>
                    <xs:element name="officialjournal.page" type="OfficialJournalPage" minOccurs="0"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                    <xs:element name="effective.enddate" type="Date" minOccurs="0"/>
                    <xs:element name="complete.abrogation.regulation.role" type="RegulationRoleTypeId" minOccurs="0"/>
                    <xs:element name="complete.abrogation.regulation.id" type="RegulationId" minOccurs="0"/>
                    <xs:element name="explicit.abrogation.regulation.role" type="RegulationRoleTypeId" minOccurs="0"/>
                    <xs:element name="explicit.abrogation.regulation.id" type="RegulationId" minOccurs="0"/>
                    <xs:element name="replacement.indicator" type="ReplacementIndicator"/>
                    <xs:element name="information.text" type="ShortDescription" minOccurs="0"/>
                    <xs:element name="approved.flag" type="ApprovedFlag"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
        "full.temporary.stop.regulation.role": "",
        "full.temporary.stop.regulation.id": "",
        "published.date": "",
        "officialjournal.number": "",
        "officialjournal.page": "",
        "validity.start.date": "",
        "validity.end.date": "",
        "effective.enddate": "",
        "complete.abrogation.regulation.role": "",
        "complete.abrogation.regulation.id": "",
        "explicit.abrogation.regulation.role": "",
        "explicit.abrogation.regulation.id": "",
        "replacement.indicator": "",
        "information.text": "",
        "approved.flag": "",
    """

    target_parser_class = FullTemporaryStopRegulationParserV2

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "full_temporary_stop_regulation_role": "3",
            "full_temporary_stop_regulation_id": "AB123400",
            "published_date": "2020-01-01",
            "officialjournal_number": "ZZ123",
            "officialjournal_page": "123",
            "validity_start_date": "2020-01-01",
            "validity_end_date": "2021-01-01",
            "effective_enddate": "2022-01-01",
            "complete_abrogation_regulation_role": "3",
            "complete_abrogation_regulation_id": "CD123123",
            "explicit_abrogation_regulation_role": "3",
            "explicit_abrogation_regulation_id": "EF123123",
            "replacement_indicator": "0",
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
        assert target.enacting_regulation__regulation_id == "AB123400"
        assert target.enacting_regulation__published_at == date(2020, 1, 1)
        assert target.enacting_regulation__official_journal_number == "ZZ123"
        assert target.enacting_regulation__official_journal_page == 123
        assert target.enacting_regulation__valid_between_lower == date(2020, 1, 1)
        assert target.enacting_regulation__valid_between_upper == date(2021, 1, 1)
        assert target.effective_end_date == date(2022, 1, 1)
        assert target.enacting_regulation__replacement_indicator == 0
        assert target.enacting_regulation__information_text == "info text"
        assert target.enacting_regulation__approved is True
