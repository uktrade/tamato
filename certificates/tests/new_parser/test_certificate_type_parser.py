from datetime import date

import pytest

from certificates.models import CertificateType
from certificates.new_import_parsers import NewCertificateTypeParser
from common.tests.util import preload_import

pytestmark = pytest.mark.django_db


@pytest.mark.new_importer
class TestNewCertificateTypeParser:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="certificate.type" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="certificate.type.code" type="CertificateTypeCode"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    target_parser_class = NewCertificateTypeParser

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "certificate_type_code": "123",
            "validity_start_date": "2023-01-22",
            "validity_end_date": "2024-01-22",
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
        assert target.valid_between_lower == date(2023, 1, 22)
        assert target.valid_between_upper == date(2024, 1, 22)

    def test_import(self, superuser):
        importer = preload_import("certificate_type_CREATE.xml", __file__)

        assert len(importer.parsed_transactions) == 1
        assert len(importer.parsed_transactions[0].parsed_messages) == 2

        target_message = importer.parsed_transactions[0].parsed_messages[0]
        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target_taric_object = target_message.taric_object
        assert target_taric_object.sid == "A"
        assert target_taric_object.valid_between_lower == date(2021, 1, 1)
        assert target_taric_object.valid_between_upper == date(2021, 12, 31)

        assert importer.issues() == []

    def test_import_update(self, superuser):
        preload_import("certificate_type_CREATE.xml", __file__, True)
        importer = preload_import("certificate_type_UPDATE.xml", __file__)

        target_message = importer.parsed_transactions[0].parsed_messages[0]

        target_taric_object = target_message.taric_object
        assert target_taric_object.sid == "A"
        assert target_taric_object.valid_between_lower == date(2021, 1, 11)
        assert target_taric_object.valid_between_upper == date(2021, 12, 31)

        assert importer.issues() == []

    def test_import_delete(self, superuser):
        preload_import("certificate_type_CREATE.xml", __file__, True)
        importer = preload_import("certificate_type_DELETE.xml", __file__)

        assert importer.issues() == []

        assert importer.can_save()
        assert CertificateType.objects.all().count() == 2
        assert CertificateType.objects.all().last().update_type == 2
