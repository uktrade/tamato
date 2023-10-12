import pytest

# note : need to import these objects to make them available to the parser
from common.tests.util import preload_import
from measures.new_import_parsers import *
from quotas.models import QuotaEvent
from quotas.new_import_parsers import *

pytestmark = pytest.mark.django_db


@pytest.mark.new_importer
class TestNewQuotaBalanceEventParser:
    """
    Could be one of any of the below:

    .. code:: XML

        <xs:element name="quota.balance.event" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="quota.definition.sid" type="SID"/>
                    <xs:element name="occurrence.timestamp" type="Timestamp"/>
                    <xs:element name="old.balance" type="QuotaAmount"/>
                    <xs:element name="new.balance" type="QuotaAmount"/>
                    <xs:element name="imported.amount" type="QuotaAmount"/>
                    <xs:element name="last.import.date.in.allocation" type="Date" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>

    """

    target_parser_class = NewQuotaBalanceEventParser

    def test_it_handles_population_from_expected_data_structure_quota_balance_event(
        self,
    ):
        expected_data_example = {
            "quota_definition_sid": "123",
            "occurrence_timestamp": "2020-09-25T14:58:58",
            "old_balance": "234000",
            "new_balance": "19000",
            "imported_amount": "123123",
            "last_import_date_in_allocation": "2021-07-04",
        }

        target = self.target_parser_class()

        target.populate(
            1,  # transaction id
            target.record_code,
            target.subrecord_code,
            1,  # sequence number
            expected_data_example,
        )

        assert target.occurrence_timestamp == datetime(2020, 9, 25, 14, 58, 58)
        assert target.quota_definition__sid == 123
        assert target.new_balance == "19000"
        assert target.old_balance == "234000"
        assert target.imported_amount == "123123"
        assert target.last_import_date_in_allocation == "2021-07-04"

        assert (
            target.data
            == '{"new.balance": "19000", "old.balance": "234000", "imported.amount": "123123", '
            '"last.import.date.in.allocation": "2021-07-04"}'
        )

    def test_import(self, superuser):
        importer = preload_import("quota_balance_event_CREATE.xml", __file__)

        assert len(importer.parsed_transactions) == 6
        assert len(importer.parsed_transactions[5].parsed_messages) == 1

        target_message = importer.parsed_transactions[5].parsed_messages[0]

        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target = target_message.taric_object

        assert target.new_balance == "0"
        assert target.old_balance == "10"
        assert target.imported_amount == "0"
        assert target.last_import_date_in_allocation == "2021-01-01"
        assert target.quota_definition__sid == 100
        assert target.occurrence_timestamp == datetime(2020, 9, 25, 14, 58, 58)

        assert (
            target.data
            == '{"new.balance": "0", "old.balance": "10", "imported.amount": "0", '
            '"last.import.date.in.allocation": "2021-01-01"}'
        )

        assert len(importer.issues()) == 0

        assert (
            QuotaEvent.objects.all()
            .filter(subrecord_code=self.target_parser_class.subrecord_code)
            .count()
            == 1
        )

    def test_import_update(self, superuser):
        # No Updates for this object type
        preload_import("quota_balance_event_CREATE.xml", __file__, True)
        importer = preload_import("quota_balance_event_UPDATE.xml", __file__)

        assert len(importer.issues()) == 1

        assert (
            "Taric objects of type QuotaEvent can't be updated, only created and deleted"
            in str(importer.issues()[0])
        )
