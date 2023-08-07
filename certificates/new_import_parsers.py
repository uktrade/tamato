from datetime import date

from certificates.import_handlers import *
from certificates.models import Certificate
from certificates.models import CertificateDescription
from certificates.models import CertificateType
from importer.new_parsers import ModelLink
from importer.new_parsers import ModelLinkField
from importer.new_parsers import NewElementParser
from importer.parsers import NewChildPeriod
from importer.parsers import NewValidityMixin
from importer.parsers import NewWritable


class NewCertificateTypeParser(NewValidityMixin, NewWritable, NewElementParser):
    model = CertificateType
    record_code = "110"
    subrecord_code = "00"

    xml_object_tag = "certificate.type"

    value_mapping = {
        "certificate_type_code": "sid",
        "validity_start_date": "valid_between_lower",
        "validity_end_date": "valid_between_upper",
    }

    model_links = []

    identity_fields = ["sid"]

    sid: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None


class NewCertificateTypeDescriptionParser(NewWritable, NewElementParser):
    model = CertificateType
    parent_parser = NewCertificateTypeParser

    model_links = [
        ModelLink(
            models.CertificateType,
            [
                ModelLinkField("sid", "sid"),
            ],
            "certificate.type",
        ),
    ]

    value_mapping = {
        "certificate_type_code": "sid",
    }

    record_code = "110"
    subrecord_code = "05"

    xml_object_tag = "certificate.type.description"

    identity_fields = ["sid"]

    sid: str = None
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

    value_mapping = {
        "certificate_code": "sid",
        "certificate_type_code": "certificate_type__sid",
        "validity_start_date": "valid_between_lower",
        "validity_end_date": "valid_between_upper",
    }

    record_code = "205"
    subrecord_code = "00"

    xml_object_tag = "certificate"

    identity_fields = ["sid"]

    sid: int = None
    certificate_type__sid: str = None
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

    value_mapping = {
        "certificate_description_period_sid": "sid",
        "certificate_type_code": "described_certificate__certificate_type__sid",
        "certificate_code": "described_certificate__sid",
    }

    identity_fields = ["sid"]

    sid: int = None
    described_certificate__certificate_type__sid: str = None
    described_certificate__sid: str = None
    description: str = None


class NewCertificateDescriptionPeriodParser(
    NewWritable,
    NewElementParser,
    NewChildPeriod,
):
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
        ModelLink(
            models.CertificateDescription,
            [
                ModelLinkField("sid", "sid"),
            ],
            "certificate.description",
        ),
    ]

    value_mapping = {
        "certificate_description_period_sid": "sid",
        "certificate_type_code": "described_certificate__certificate_type__sid",
        "certificate_code": "described_certificate__sid",
        "validity_start_date": "validity_start",
    }

    record_code = "205"
    subrecord_code = "05"

    xml_object_tag = "certificate.description.period"

    identity_fields = ["sid"]

    sid: int = None
    described_certificate__certificate_type__sid: str = None
    described_certificate__sid: str = None
    validity_start: date = None
