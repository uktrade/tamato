from certificates.models import *
from taric_parsers.parser_model_link import *
from taric_parsers.parsers.mixins import *
from taric_parsers.parsers.taric_parser import *


class NewCertificateTypeParser(ValidityMixin, Writable, BaseTaricParser):
    model = CertificateType
    record_code = "110"
    subrecord_code = "00"
    allow_update_without_children = True

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


class NewCertificateTypeDescriptionParser(Writable, BaseTaricParser):
    model = CertificateType
    parent_parser = NewCertificateTypeParser

    model_links = [
        ModelLink(
            CertificateType,
            [
                ModelLinkField("sid", "sid"),
            ],
            "certificate.type",
        ),
    ]

    value_mapping = {
        "certificate_type_code": "sid",
    }

    deletes_allowed = False

    record_code = "110"
    subrecord_code = "05"

    xml_object_tag = "certificate.type.description"

    identity_fields = ["sid"]

    sid: str = None
    description: str = None


class NewCertificateParser(ValidityMixin, Writable, BaseTaricParser):
    model = Certificate

    model_links = [
        ModelLink(
            CertificateType,
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


class NewCertificateDescriptionParser(Writable, BaseTaricParser):
    model = CertificateDescription
    allow_update_without_children = True
    model_links = [
        ModelLink(
            CertificateType,
            [
                ModelLinkField("described_certificate__certificate_type__sid", "sid"),
            ],
            "certificate.type",
        ),
        ModelLink(
            Certificate,
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

    identity_fields = ["sid", "described_certificate__sid"]

    sid: int = None
    described_certificate__certificate_type__sid: str = None
    described_certificate__sid: str = None
    description: str = None


class NewCertificateDescriptionPeriodParser(
    Writable,
    BaseTaricParser,
    ChildPeriod,
):
    model = CertificateDescription
    parent_parser = NewCertificateDescriptionParser

    model_links = [
        ModelLink(
            CertificateType,
            [
                ModelLinkField("described_certificate__certificate_type__sid", "sid"),
            ],
            "certificate.type",
        ),
        ModelLink(
            Certificate,
            [
                ModelLinkField("described_certificate__sid", "sid"),
            ],
            "certificate",
        ),
        ModelLink(
            CertificateDescription,
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

    deletes_allowed = False

    sid: int = None
    described_certificate__certificate_type__sid: str = None
    described_certificate__sid: str = None
    validity_start: date = None
