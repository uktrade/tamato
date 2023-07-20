import os

import pytest

# note : need to import these objects to make them available to the parser
from certificates.new_import_parsers import NewCertificateDescriptionParser
from importer import new_importer

pytestmark = pytest.mark.django_db


def get_test_xml_file(file_name):
    path_to_current_file = os.path.realpath(__file__)
    current_directory = os.path.split(path_to_current_file)[0]
    return os.path.join(current_directory, "importer_examples", file_name)


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

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "certificate_description_period_sid": "555",
            "language_id": "EN",  # gets ignored, but will come in from import
            "certificate_type_code": "666",
            "certificate_code": "777",
            "description": "this is a description",
        }

        target = NewCertificateDescriptionParser()

        target.populate(
            1,  # transaction id
            target.record_code,
            target.subrecord_code,
            1,  # sequence number
            expected_data_example,
        )

        # verify all properties
        assert target.sid == "555"  # converts "certificate_code" to sid
        assert (
            target.described_certificate__certificate_type__sid == "666"
        )  # converts "certificate_code" to sid
        assert target.described_certificate__sid == "777"
        assert target.description == "this is a description"

    def test_import(self, superuser):
        file_to_import = get_test_xml_file("certificate_description_CREATE.xml")

        importer = new_importer.NewImporter(
            file_to_import,
            import_title="Importing stuff",
            author_username=superuser.username,
        )

        # check there is one AdditionalCodeType imported
        assert len(importer.parsed_transactions) == 1
        assert len(importer.parsed_transactions[0].parsed_messages) == 4

        target_message = importer.parsed_transactions[0].parsed_messages[3]

        assert target_message.record_code == NewCertificateDescriptionParser.record_code
        assert (
            target_message.subrecord_code
            == NewCertificateDescriptionParser.subrecord_code
        )
        assert type(target_message.taric_object) == NewCertificateDescriptionParser

        # check properties for additional code
        target_taric_object = target_message.taric_object
        assert target_taric_object.sid == "999"
        assert target_taric_object.described_certificate__certificate_type__sid == "777"
        assert target_taric_object.described_certificate__sid == "123"
        assert target_taric_object.description == "This is a description"

        for message in importer.parsed_transactions[0].parsed_messages:
            # check for issues
            assert len(message.taric_object.issues) == 0
