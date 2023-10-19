from datetime import date

import pytest

# note : need to import these objects to make them available to the parser
from common.tests.util import preload_import
from quotas.models import QuotaOrderNumberOrigin
from taric_parsers.parsers.geo_area_parser import *
from taric_parsers.parsers.quota_parser import *

pytestmark = pytest.mark.django_db


@pytest.mark.new_importer
class TestNewQuotaOrderNumberOriginParser:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="quota.order.number.origin" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="quota.order.number.origin.sid" type="SID"/>
                    <xs:element name="quota.order.number.sid" type="SID"/>
                    <xs:element name="geographical.area.id" type="GeographicalAreaId"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                    <xs:element name="geographical.area.sid" type="SID"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    target_parser_class = NewQuotaOrderNumberOriginParser

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "quota_order_number_origin_sid": "555",
            "quota_order_number_sid": "123",
            "geographical_area_id": "ABCD",  # gets ignored, but will come in from import
            "validity_start_date": "2020-01-01",
            "validity_end_date": "2020-12-01",
            "geographical_area_sid": "1234",
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
        assert target.sid == 555  # converts "certificate_code" to sid
        assert target.order_number__sid == 123  # converts "certificate_code" to sid
        assert target.geographical_area__sid == 1234
        assert target.geographical_area__area_id == "ABCD"
        assert target.valid_between_lower == date(2020, 1, 1)
        assert target.valid_between_upper == date(2020, 12, 1)

    def test_import(self, superuser):
        importer = preload_import(
            "quota_order_number_origin_CREATE.xml",
            __file__,
        )

        assert len(importer.parsed_transactions) == 4

        target_message = importer.parsed_transactions[3].parsed_messages[0]

        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        # check properties
        target = target_message.taric_object

        assert target.sid == 123
        assert target.order_number__sid == 7
        assert target.geographical_area__sid == 8
        assert target.geographical_area__area_id == "AB01"
        assert target.valid_between_lower == date(2021, 1, 1)
        assert target.valid_between_upper == date(2022, 1, 1)

        assert len(importer.issues()) == 0
        assert QuotaOrderNumberOrigin.objects.all().count() == 1

    def test_import_update(self, superuser):
        preload_import(
            "quota_order_number_origin_CREATE.xml",
            __file__,
            True,
        )
        importer = preload_import(
            "quota_order_number_origin_UPDATE.xml",
            __file__,
        )
        target_message = importer.parsed_transactions[0].parsed_messages[0]

        # check properties
        target = target_message.taric_object

        assert target.sid == 123
        assert target.order_number__sid == 7
        assert target.geographical_area__sid == 8
        assert target.geographical_area__area_id == "AB01"
        assert target.valid_between_lower == date(2021, 1, 11)
        assert target.valid_between_upper == date(2022, 1, 1)

        assert len(importer.issues()) == 0

        assert QuotaOrderNumberOrigin.objects.all().count() == 2
