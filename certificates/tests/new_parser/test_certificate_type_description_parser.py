import os

import pytest

# note : need to import these objects to make them available to the parser
from certificates.new_import_parsers import NewCertificateTypeDescriptionParser
from importer import new_importer

pytestmark = pytest.mark.django_db


def get_test_xml_file(file_name):
    path_to_current_file = os.path.realpath(__file__)
    current_directory = os.path.split(path_to_current_file)[0]
    return os.path.join(current_directory, "importer_examples", file_name)


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

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "certificate_type_code": "123",
            "language_id": "EN",
            "description": "Some description",
        }

        target = NewCertificateTypeDescriptionParser()

        target.populate(
            1,  # transaction id
            target.record_code,
            target.subrecord_code,
            1,  # sequence number
            expected_data_example,
        )

        # verify all properties
        assert target.sid == "123"  # converts "certificate_type_code" to sid
        # assert target.language_id == 'EN'
        assert target.description == "Some description"

    def test_import(self, superuser):
        file_to_import = get_test_xml_file("certificate_type_description_CREATE.xml")

        importer = new_importer.NewImporter(
            file_to_import,
            import_title="Importing stuff",
            author_username=superuser.username,
        )

        # check there is one AdditionalCodeType imported
        assert len(importer.parsed_transactions) == 1
        assert len(importer.parsed_transactions[0].parsed_messages) == 2

        target_message = importer.parsed_transactions[0].parsed_messages[1]

        assert (
            target_message.record_code
            == NewCertificateTypeDescriptionParser.record_code
        )
        assert (
            target_message.subrecord_code
            == NewCertificateTypeDescriptionParser.subrecord_code
        )
        assert type(target_message.taric_object) == NewCertificateTypeDescriptionParser

        # check properties for additional code
        target_taric_object = target_message.taric_object
        assert target_taric_object.sid == "333"
        assert target_taric_object.description == "some description"

        for message in importer.parsed_transactions[0].parsed_messages:
            # check for issues
            assert len(message.taric_object.issues) == 0
