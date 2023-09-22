import pytest

# note : need to import these objects to make them available to the parser
from certificates.new_import_parsers import *
from common.tests import factories
from common.tests.util import get_test_xml_file
from importer import new_importer
from workbaskets.validators import WorkflowStatus

pytestmark = pytest.mark.django_db


@pytest.mark.new_importer
class TestNewCertificateDescriptionParser:
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

    target_parser_class = NewCertificateDescriptionParser

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
        file_to_import = get_test_xml_file(
            "certificate_description_CREATE.xml",
            __file__,
        )

        workbasket = factories.WorkBasketFactory.create(status=WorkflowStatus.EDITING)
        import_batch = factories.ImportBatchFactory.create(workbasket=workbasket)

        importer = new_importer.NewImporter(
            import_batch=import_batch,
            taric3_file=file_to_import,
            import_title="Importing stuff",
            author_username=superuser.username,
        )

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

        assert len(importer.issues()) == 0
