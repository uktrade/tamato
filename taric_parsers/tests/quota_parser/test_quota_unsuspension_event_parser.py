from datetime import timezone

import pytest

# note : need to import these objects to make them available to the parser
from common.tests.util import preload_import
from quotas.models import QuotaEvent
from taric_parsers.parsers.measure_parser import *
from taric_parsers.parsers.quota_parser import *

pytestmark = pytest.mark.django_db


@pytest.mark.importer_v2
class TestQuotaEventParserV2:
    """
    Could be one of any of the below:

    .. code:: XML

        <xs:element name="quota.unsuspension.event" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="quota.definition.sid" type="SID"/>
                    <xs:element name="occurrence.timestamp" type="Timestamp"/>
                    <xs:element name="unsuspension.date" type="Date"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    target_parser_class = QuotaUnsuspensionEventParserV2

    def test_it_handles_population_from_expected_data_structure_quota_balance_event(
        self,
    ):
        expected_data_example = {
            "quota_definition_sid": "123",
            "occurrence_timestamp": "2020-09-25T14:58:58Z",
            "unsuspension_date": "2021-07-04",
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
        assert target.occurrence_timestamp == datetime(
            2020,
            9,
            25,
            14,
            58,
            58,
            tzinfo=timezone.utc,
        )
        assert target.quota_definition__sid == 123
        assert target.unsuspension_date == "2021-07-04"

        assert target.data == '{"unsuspension.date": "2021-07-04"}'

    def test_import(self, superuser):
        importer = preload_import(
            "quota_unsuspension_event_CREATE.xml",
            __file__,
        )

        assert len(importer.parsed_transactions) == 6
        assert len(importer.parsed_transactions[5].parsed_messages) == 1

        target_message = importer.parsed_transactions[5].parsed_messages[0]

        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target = target_message.taric_object

        assert target.quota_definition__sid == 100
        assert target.occurrence_timestamp == datetime(
            2020,
            9,
            25,
            14,
            58,
            58,
            tzinfo=timezone.utc,
        )
        assert target.unsuspension_date == "2021-01-01"

        assert target.data == '{"unsuspension.date": "2021-01-01"}'

        assert len(importer.issues()) == 0

        assert (
            QuotaEvent.objects.all()
            .filter(subrecord_code=self.target_parser_class.subrecord_code)
            .count()
            == 1
        )

    def test_import_update(self, superuser):
        preload_import("quota_unsuspension_event_CREATE.xml", __file__, True)
        importer = preload_import("quota_unsuspension_event_UPDATE.xml", __file__)

        assert len(importer.issues()) == 1

        assert "Taric objects of type QuotaEvent can't be updated" in str(
            importer.issues()[0],
        )

    def test_import_delete(self, superuser):
        preload_import("quota_unsuspension_event_CREATE.xml", __file__, True)
        importer = preload_import("quota_unsuspension_event_DELETE.xml", __file__)

        assert len(importer.issues()) == 0

        assert QuotaEvent.objects.all().count() == 2
