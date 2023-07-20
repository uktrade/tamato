import os
from datetime import date

import pytest

# note : need to import these objects to make them available to the parser
from certificates.new_import_parsers import NewCertificateParser
from importer import new_importer

pytestmark = pytest.mark.django_db


def get_test_xml_file(file_name):
    path_to_current_file = os.path.realpath(__file__)
    current_directory = os.path.split(path_to_current_file)[0]
    return os.path.join(current_directory, "importer_examples", file_name)


class TestNewCertificateParser:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="certificate" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="certificate.type.code" type="CertificateTypeCode"/>
                    <xs:element name="certificate.code" type="CertificateCode"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "certificate_code": "456",
            "certificate_type_code": "891",
            "validity_start_date": "2023-01-22",
            "validity_end_date": "2024-01-22",
        }

        target = NewCertificateParser()

        target.populate(
            1,  # transaction id
            target.record_code,
            target.subrecord_code,
            1,  # sequence number
            expected_data_example,
        )

        # verify all properties
        assert target.sid == "456"  # converts "certificate_code" to sid
        assert (
            target.certificate_type__sid == "891"
        )  # converts "certificate_code" to sid
        assert target.valid_between_lower == date(2023, 1, 22)
        assert target.valid_between_upper == date(2024, 1, 22)

    def test_import(self, superuser):
        file_to_import = get_test_xml_file("certificate_CREATE.xml")

        importer = new_importer.NewImporter(
            file_to_import,
            import_title="Importing stuff",
            author_username=superuser.username,
        )

        # check there is one AdditionalCodeType imported
        assert len(importer.parsed_transactions) == 1
        assert len(importer.parsed_transactions[0].parsed_messages) == 3

        target_message = importer.parsed_transactions[0].parsed_messages[2]

        assert target_message.record_code == NewCertificateParser.record_code
        assert target_message.subrecord_code == NewCertificateParser.subrecord_code
        assert type(target_message.taric_object) == NewCertificateParser

        # check properties for additional code
        target_taric_object = target_message.taric_object
        assert target_taric_object.sid == "123"
        assert target_taric_object.certificate_type__sid == "333"
        assert target_taric_object.valid_between_lower == date(2021, 1, 1)
        assert target_taric_object.valid_between_upper == date(2021, 12, 31)

        for message in importer.parsed_transactions[0].parsed_messages:
            # check for issues
            assert len(message.taric_object.issues) == 0
