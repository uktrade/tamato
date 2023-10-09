from datetime import date

import pytest

# note : need to import these objects to make them available to the parser
from common.tests.util import preload_import
from quotas.models import QuotaOrderNumber
from quotas.new_import_parsers import NewQuotaOrderNumberParser

pytestmark = pytest.mark.django_db


@pytest.mark.new_importer
class TestNewQuotaOrderNumberParser:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="quota.order.number" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="quota.order.number.sid" type="SID"/>
                    <xs:element name="quota.order.number.id" type="OrderNumber"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    target_parser_class = NewQuotaOrderNumberParser

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "quota_order_number_sid": "7",
            "quota_order_number_id": "010000",
            "validity_start_date": "2020-01-01",
            "validity_end_date": "2020-12-01",
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
        assert target.sid == 7
        assert target.order_number == "010000"
        assert target.valid_between_lower == date(2020, 1, 1)
        assert target.valid_between_upper == date(2020, 12, 1)

    def test_import(self, superuser):
        importer = preload_import("quota_order_number_CREATE.xml", __file__)

        assert len(importer.parsed_transactions) == 1

        target_message = importer.parsed_transactions[0].parsed_messages[0]

        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target = target_message.taric_object

        assert target.sid == 7
        assert target.order_number == "054515"
        assert target.valid_between_lower == date(2021, 1, 1)
        assert target.valid_between_upper is None

        assert len(importer.issues()) == 0

        assert QuotaOrderNumber.objects.all().count() == 1
