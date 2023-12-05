import pytest

from common.tests.util import preload_import
from common.validators import UpdateType

# note : need to import these objects to make them available to the parser
from taric_parsers.parsers.certificate_parser import *

pytestmark = pytest.mark.django_db


@pytest.mark.importer_v2
class TestCertificateDescriptionParserV2:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="certificate.description" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="certificate.description.period.sid" type="SID"/>
                    <xs:element name="language.id" type="LanguageId"/>
                    <xs:element name="certificate.type.code" type="CertificateTypeCode"/>
                    <xs:element name="certificate.code" type="CertificateCode"/>
                    <xs:element name="description" type="ShortDescription" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    target_parser_class = CertificateDescriptionParserV2

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "certificate_description_period_sid": 555,
            "language_id": "EN",  # gets ignored, but will come in from import
            "certificate_type_code": "666",
            "certificate_code": "777",
            "description": "this is a description",
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
        assert target.sid == 555
        assert target.described_certificate__certificate_type__sid == "666"
        assert target.described_certificate__sid == "777"
        assert target.description == "this is a description"

    def test_import(self, superuser):
        importer = preload_import("certificate_description_CREATE.xml", __file__)

        assert len(importer.parsed_transactions) == 1
        assert len(importer.parsed_transactions[0].parsed_messages) == 5

        target_message = importer.parsed_transactions[0].parsed_messages[4]
        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target = target_message.taric_object
        assert target.sid == 8
        assert target.described_certificate__certificate_type__sid == "A"
        assert target.described_certificate__sid == "123"
        assert target.description == "This is a description"

        assert importer.issues() == []

    def test_import_update(self, superuser):
        preload_import("certificate_description_CREATE.xml", __file__, True)
        importer = preload_import("certificate_description_UPDATE.xml", __file__)

        target_message = importer.parsed_transactions[0].parsed_messages[0]
        target = target_message.taric_object

        assert importer.issues() == []

        assert target.sid == 8
        assert target.described_certificate__certificate_type__sid == "A"
        assert target.described_certificate__sid == "123"
        assert target.description == "This is a description with changes"

    def test_import_delete(self):
        preload_import(
            "certificate_description_CREATE.xml",
            __file__,
            True,
        )
        importer = preload_import(
            "certificate_description_DELETE.xml",
            __file__,
        )
        # check for issues
        assert importer.issues() == []
        assert importer.can_save()
        assert CertificateDescription.objects.all().count() == 2
        assert (
            CertificateDescription.objects.all().last().update_type == UpdateType.DELETE
        )
