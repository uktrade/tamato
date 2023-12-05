from datetime import date

import pytest

from certificates.models import Certificate
from common.tests.util import preload_import
from common.validators import UpdateType

# note : need to import these objects to make them available to the parser
from taric_parsers.parsers.certificate_parser import *

pytestmark = pytest.mark.django_db


@pytest.mark.importer_v2
class TestCertificateParserV2:
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

    target_parser_class = CertificateParserV2

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "certificate_code": "456",
            "certificate_type_code": "891",
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
        assert target.sid == 456
        assert target.certificate_type__sid == "891"
        assert target.valid_between_lower == date(2023, 1, 22)
        assert target.valid_between_upper == date(2024, 1, 22)

    def test_import(self, superuser):
        importer = preload_import("certificate_CREATE.xml", __file__)

        assert len(importer.parsed_transactions) == 1
        assert len(importer.parsed_transactions[0].parsed_messages) == 3

        target_message = importer.parsed_transactions[0].parsed_messages[2]

        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target_taric_object = target_message.taric_object
        assert target_taric_object.sid == 123
        assert target_taric_object.certificate_type__sid == "A"
        assert target_taric_object.valid_between_lower == date(2021, 1, 1)
        assert target_taric_object.valid_between_upper == date(2021, 12, 31)

        assert importer.issues() == []

    def test_import_update(self, superuser):
        preload_import("certificate_CREATE.xml", __file__, True)
        importer = preload_import("certificate_UPDATE.xml", __file__)

        target_message = importer.parsed_transactions[0].parsed_messages[0]
        target_taric_object = target_message.taric_object

        assert target_taric_object.sid == 123
        assert target_taric_object.certificate_type__sid == "A"
        assert target_taric_object.valid_between_lower == date(2021, 1, 11)
        assert target_taric_object.valid_between_upper == date(2021, 12, 31)

        assert importer.issues() == []

    def test_import_delete(self):
        preload_import(
            "certificate_CREATE.xml",
            __file__,
            True,
        )
        importer = preload_import(
            "certificate_DELETE.xml",
            __file__,
        )
        # check for issues
        assert importer.issues() == []
        assert importer.can_save()
        assert Certificate.objects.all().count() == 2
        assert Certificate.objects.all().last().update_type == UpdateType.DELETE
