from datetime import date

from certificates.import_handlers import *
from certificates.models import Certificate
from certificates.models import CertificateDescription
from certificates.models import CertificateType
from importer.new_parsers import ModelLink
from importer.new_parsers import ModelLinkField
from importer.new_parsers import NewElementParser
from importer.parsers import NewValidityMixin
from importer.parsers import NewWritable


class NewCertificateTypeParser(NewValidityMixin, NewWritable, NewElementParser):
    # handler = CertificateTypeHandler
    model = CertificateType
    record_code = "110"
    subrecord_code = "00"

    xml_object_tag = "certificate.type"

    sid: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None


class NewCertificateTypeDescriptionParser(NewWritable, NewElementParser):
    model = CertificateType
    parent_parser = NewCertificateTypeParser

    record_code = "110"
    subrecord_code = "05"

    xml_object_tag = "certificate.type.description"

    sid: str = None
    language_id: str = None
    description: str = None


class NewCertificateParser(NewValidityMixin, NewWritable, NewElementParser):
    model = Certificate

    model_links = [
        ModelLink(
            models.CertificateType,
            [
                ModelLinkField("certificate_type__sid", "sid"),
            ],
            "certificate.type",
        ),
    ]

    record_code = "205"
    subrecord_code = "00"

    xml_object_tag = "certificate"

    certificate_type__sid: str = None
    sid: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None


class NewCertificateDescriptionParser(NewWritable, NewElementParser):
    model = CertificateDescription
    model_links = [
        ModelLink(
            models.CertificateType,
            [
                ModelLinkField("described_certificate__certificate_type__sid", "sid"),
            ],
            "certificate.type",
        ),
        ModelLink(
            models.Certificate,
            [
                ModelLinkField("described_certificate__sid", "sid"),
            ],
            "certificate",
        ),
    ]

    record_code = "205"
    subrecord_code = "10"

    xml_object_tag = "certificate.description"

    sid: str = None
    language_id: str = None
    described_certificate__certificate_type__sid: str = None
    described_certificate__sid: str = None
    description: str = None


class NewCertificateDescriptionPeriodParser(NewWritable, NewElementParser):
    model = CertificateDescription
    parent_parser = NewCertificateDescriptionParser

    model_links = [
        ModelLink(
            models.CertificateType,
            [
                ModelLinkField("described_certificate__certificate_type__sid", "sid"),
            ],
            "certificate.type",
        ),
        ModelLink(
            models.Certificate,
            [
                ModelLinkField("described_certificate__sid", "sid"),
            ],
            "certificate",
        ),
    ]

    record_code = "205"
    subrecord_code = "05"

    xml_object_tag = "certificate.description.period"

    sid: str = None
    described_certificate__certificate_type__sid: str = None
    described_certificate__sid: str = None
    validity_start: date = None
