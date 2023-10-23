import pytest

# note : need to import these objects to make them available to the parser
from common.tests.util import preload_import
from quotas.models import QuotaAssociation
from taric_parsers.parsers.measure_parser import *
from taric_parsers.parsers.quota_parser import *

pytestmark = pytest.mark.django_db


@pytest.mark.new_importer
class TestNewQuotaAssociationParser:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="quota.association" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="main.quota.definition.sid" type="SID"/>
                    <xs:element name="sub.quota.definition.sid" type="SID"/>
                    <xs:element name="relation.type" type="RelationType"/>
                    <xs:element name="coefficient" type="QuotaCoefficient" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    target_parser_class = NewQuotaAssociationParser

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "main_quota_definition_sid": "12",
            "sub_quota_definition_sid": "13",  # gets ignored, but will come in from import
            "relation_type": "ZZ",
            "coefficient": "12.432",
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
        assert target.main_quota__sid == 12
        assert target.sub_quota__sid == 13
        assert target.sub_quota_relation_type == "ZZ"
        assert target.coefficient == 12.432

    def test_import(self, superuser):
        importer = preload_import("quota_association_CREATE.xml", __file__)

        assert len(importer.parsed_transactions) == 6

        target_message = importer.parsed_transactions[5].parsed_messages[0]

        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target = target_message.taric_object
        assert target.main_quota__sid == 99
        assert target.sub_quota__sid == 100
        assert target.sub_quota_relation_type == "EQ"
        assert target.coefficient == 1.6

        assert len(importer.issues()) == 0
        assert QuotaAssociation.objects.all().count() == 1

    def test_import_update(self, superuser):
        preload_import("quota_association_CREATE.xml", __file__, True)
        importer = preload_import("quota_association_UPDATE.xml", __file__)

        target_message = importer.parsed_transactions[0].parsed_messages[0]

        target = target_message.taric_object

        assert target.main_quota__sid == 99
        assert target.sub_quota__sid == 100
        assert target.sub_quota_relation_type == "EQ"
        assert target.coefficient == 1.1

        assert len(importer.issues()) == 0

        assert QuotaAssociation.objects.all().count() == 2

    def test_import_delete(self, superuser):
        preload_import("quota_association_CREATE.xml", __file__, True)
        importer = preload_import("quota_association_DELETE.xml", __file__)

        assert len(importer.issues()) == 0

        assert QuotaAssociation.objects.all().count() == 2
