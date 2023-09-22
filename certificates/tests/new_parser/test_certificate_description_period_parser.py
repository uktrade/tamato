from datetime import date

import pytest

from certificates.models import CertificateDescription

# note : need to import these objects to make them available to the parser
from certificates.new_import_parsers import NewCertificateDescriptionPeriodParser
from common.tests import factories
from common.tests.util import get_test_xml_file
from importer import new_importer
from workbaskets.validators import WorkflowStatus

pytestmark = pytest.mark.django_db


@pytest.mark.new_importer
class TestNewCertificateDescriptionPeriodParser:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="certificate.description.period" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="certificate.description.period.sid" type="SID"/>
                    <xs:element name="certificate.type.code" type="CertificateTypeCode"/>
                    <xs:element name="certificate.code" type="CertificateCode"/>
                    <xs:element name="validity.start.date" type="Date"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    target_parser_class = NewCertificateDescriptionPeriodParser

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "certificate_description_period_sid": "123",
            "certificate_type_code": "A",
            "certificate_code": "BBB",
            "validity_start_date": "2021-01-01",
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
        assert target.sid == 123
        assert target.described_certificate__certificate_type__sid == "A"
        assert target.described_certificate__sid == "BBB"
        assert target.validity_start == date(2021, 1, 1)

    def test_import(self, superuser):
        file_to_import = get_test_xml_file(
            "certificate_description_period_CREATE.xml",
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

        target_message = importer.parsed_transactions[0].parsed_messages[3]
        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target_taric_object = target_message.taric_object
        assert target_taric_object.sid == 9
        assert target_taric_object.described_certificate__certificate_type__sid == "A"
        assert target_taric_object.described_certificate__sid == "123"
        assert target_taric_object.validity_start == date(2021, 12, 31)

        target = CertificateDescription.objects.all().last()
        assert target.validity_start == target_taric_object.validity_start
        assert target.sid == int(target_taric_object.sid)

        for message in importer.parsed_transactions[0].parsed_messages:
            # check for issues
            assert len(message.taric_object.issues) == 0
