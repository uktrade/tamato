from datetime import date

import pytest

# note : need to import these objects to make them available to the parser
from common.tests.util import preload_import
from quotas.models import QuotaBlocking
from taric_parsers.parsers.measure_parser import *
from taric_parsers.parsers.quota_parser import *

pytestmark = pytest.mark.django_db


@pytest.mark.importer_v2
class TestNewQuotaBlockingParser:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="quota.blocking.period" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="quota.blocking.period.sid" type="SID"/>
                    <xs:element name="quota.definition.sid" type="SID"/>
                    <xs:element name="blocking.start.date" type="Date"/>
                    <xs:element name="blocking.end.date" type="Date"/>
                    <xs:element name="blocking.period.type" type="QuotaBlockingPeriodType"/>
                    <xs:element name="description" type="ShortDescription" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    target_parser_class = NewQuotaBlockingParser

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "quota_blocking_period_sid": "123",
            "quota_definition_sid": "14",  # gets ignored, but will come in from import
            "blocking_start_date": "2020-01-01",
            "blocking_end_date": "2020-12-01",
            "blocking_period_type": "0",
            "description": "Some Description",
        }

        target = self.target_parser_class()

        target.populate(
            1,  # transaction id
            target.record_code,
            target.subrecord_code,
            1,  # sequence number
            expected_data_example,
        )

        assert target.sid == 123
        assert target.quota_definition__sid == 14
        assert target.valid_between_lower == date(2020, 1, 1)
        assert target.valid_between_upper == date(2020, 12, 1)
        assert target.blocking_period_type == 0
        assert target.description == "Some Description"

    def test_import(self, superuser):
        importer = preload_import("quota_blocking_period_CREATE.xml", __file__)

        assert len(importer.parsed_transactions) == 6

        target_message = importer.parsed_transactions[5].parsed_messages[0]

        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target = target_message.taric_object
        assert target.sid == 22
        assert target.quota_definition__sid == 99
        assert target.valid_between_lower == date(2021, 1, 1)
        assert target.valid_between_upper == date(2022, 1, 1)
        assert target.blocking_period_type == 3
        assert target.description == "Some Description"

        assert QuotaBlocking.objects.all().count() == 1

        assert len(importer.issues()) == 0

    def test_import_update(self, superuser):
        preload_import("quota_blocking_period_CREATE.xml", __file__, True)
        importer = preload_import("quota_blocking_period_UPDATE.xml", __file__)

        target_message = importer.parsed_transactions[0].parsed_messages[0]

        target = target_message.taric_object

        assert target.sid == 22
        assert target.quota_definition__sid == 99
        assert target.valid_between_lower == date(2021, 1, 11)
        assert target.valid_between_upper == date(2022, 1, 1)
        assert target.blocking_period_type == 3
        assert target.description == "Some Description with changes"

        assert len(importer.issues()) == 0

        assert QuotaBlocking.objects.all().count() == 2

    def test_import_delete(self, superuser):
        preload_import("quota_blocking_period_CREATE.xml", __file__, True)
        importer = preload_import("quota_blocking_period_DELETE.xml", __file__)

        assert len(importer.issues()) == 0

        assert QuotaBlocking.objects.all().count() == 2
