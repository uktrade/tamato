from datetime import date

import pytest

# note : need to import these objects to make them available to the parser
from common.tests.util import preload_import
from measures.new_import_parsers import *
from quotas.models import QuotaSuspension
from quotas.new_import_parsers import *

pytestmark = pytest.mark.django_db


@pytest.mark.new_importer
class TestNewQuotaSuspensionParser:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="quota.suspension.period" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="quota.suspension.period.sid" type="SID"/>
                    <xs:element name="quota.definition.sid" type="SID"/>
                    <xs:element name="suspension.start.date" type="Date"/>
                    <xs:element name="suspension.end.date" type="Date"/>
                    <xs:element name="description" type="ShortDescription" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    target_parser_class = NewQuotaSuspensionParser

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "quota_suspension_period_sid": "456",
            "quota_definition_sid": "123",
            "suspension_start_date": "2020-01-01",
            "suspension_end_date": "2021-01-01",
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

        # verify all properties
        assert target.sid == 456
        assert target.quota_definition__sid == 123
        assert target.valid_between_lower == date(2020, 1, 1)
        assert target.valid_between_upper == date(2021, 1, 1)
        assert target.description == "Some Description"

    def test_import(self, superuser):
        importer = preload_import("quota_suspension_CREATE.xml", __file__)

        assert len(importer.parsed_transactions) == 6

        target_message = importer.parsed_transactions[5].parsed_messages[0]

        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target = target_message.taric_object

        assert target.sid == 123
        assert target.quota_definition__sid == 99
        assert target.valid_between_lower == date(2021, 1, 1)
        assert target.valid_between_upper == date(2022, 1, 1)
        assert target.description == "Some Description"

        assert len(importer.issues()) == 0
        assert QuotaSuspension.objects.all().count() == 1
