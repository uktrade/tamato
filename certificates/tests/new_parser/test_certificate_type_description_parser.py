import pytest

# note : need to import these objects to make them available to the parser
from certificates.new_import_parsers import NewCertificateTypeDescriptionParser
from common.tests.util import preload_import

pytestmark = pytest.mark.django_db


@pytest.mark.new_importer
class TestNewCertificateTypeDescriptionParser:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="certificate.type.description" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="certificate.type.code" type="CertificateTypeCode"/>
                    <xs:element name="language.id" type="LanguageId"/>
                    <xs:element name="description" type="ShortDescription" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    target_parser_class = NewCertificateTypeDescriptionParser

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "certificate_type_code": "123",
            "language_id": "EN",
            "description": "Some description",
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
        assert target.sid == "123"
        assert target.description == "Some description"

    def test_import(self, superuser):
        importer = preload_import("certificate_type_description_CREATE.xml", __file__)

        assert len(importer.parsed_transactions) == 1
        assert len(importer.parsed_transactions[0].parsed_messages) == 2

        target_message = importer.parsed_transactions[0].parsed_messages[1]
        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target = target_message.taric_object
        assert target.sid == "A"
        assert target.description == "some description"
        assert importer.issues() == []

    def test_import_update(self, superuser):
        preload_import("certificate_type_description_CREATE.xml", __file__, True)
        importer = preload_import("certificate_type_description_UPDATE.xml", __file__)

        target_message = importer.parsed_transactions[0].parsed_messages[0]
        target = target_message.taric_object

        assert target.sid == "A"
        assert target.description == "some description with changes"

        assert importer.issues() == []
