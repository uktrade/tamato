import pytest

# note : need to import these objects to make them available to the parser
from common.tests.util import preload_import
from geo_areas.new_import_parsers import *
from quotas.models import QuotaOrderNumberOriginExclusion
from quotas.new_import_parsers import *

pytestmark = pytest.mark.django_db


@pytest.mark.new_importer
class TestNewQuotaOrderNumberOriginExclusionParser:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="quota.order.number.origin.exclusions" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="quota.order.number.origin.sid" type="SID"/>
                    <xs:element name="excluded.geographical.area.sid" type="SID"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    target_parser_class = NewQuotaOrderNumberOriginExclusionParser

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "quota_order_number_origin_sid": "30",
            "excluded_geographical_area_sid": "10",
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
        assert target.origin__sid == 30
        assert target.excluded_geographical_area__sid == 10

    def test_import(self, superuser):
        importer = preload_import(
            "quota_order_number_origin_exclusion_CREATE.xml",
            __file__,
        )

        assert len(importer.parsed_transactions) == 5

        target_message = importer.parsed_transactions[4].parsed_messages[0]

        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        # check properties
        target = target_message.taric_object
        assert target.origin__sid == 123
        assert target.excluded_geographical_area__sid == 8

        assert len(importer.issues()) == 0
        assert QuotaOrderNumberOriginExclusion.objects.all().count() == 1

    def test_import_update(self, superuser):
        preload_import(
            "quota_order_number_origin_exclusion_CREATE.xml",
            __file__,
            True,
        )
        importer = preload_import(
            "quota_order_number_origin_exclusion_UPDATE.xml",
            __file__,
        )

        target_message = importer.parsed_transactions[0].parsed_messages[0]

        # check properties
        target = target_message.taric_object
        assert target.origin__sid == 123
        assert target.excluded_geographical_area__sid == 8

        assert len(importer.issues()) == 0

        assert QuotaOrderNumberOriginExclusion.objects.all().count() == 2
