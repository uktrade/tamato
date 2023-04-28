from datetime import date

from certificates.import_handlers import *
from importer.new_parsers import NewElementParser
from importer.parsers import NewValidityMixin
from importer.parsers import NewWritable


class NewCertificateTypeParser(NewValidityMixin, NewWritable, NewElementParser):
    handler = CertificateTypeHandler
    record_code = "110"
    subrecord_code = "00"

    xml_object_tag = "certificate.type"

    sid: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None


class NewCertificateTypeDescriptionParser(NewWritable, NewElementParser):
    handler = CertificateTypeDescriptionHandler
    record_code = "110"
    subrecord_code = "05"

    xml_object_tag = "certificate.type.description"

    sid: str = None
    language_id: str = None
    description: str = None


class NewCertificateParser(NewValidityMixin, NewWritable, NewElementParser):
    handler = CertificateHandler
    record_code = "205"
    subrecord_code = "00"

    xml_object_tag = "certificate"

    certificate_type__sid: str = None
    sid: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None


class NewCertificateDescriptionParser(NewWritable, NewElementParser):
    handler = CertificateDescriptionHandler
    record_code = "205"
    subrecord_code = "10"

    xml_object_tag = "certificate.description"

    sid: str = None
    language_id: str = None
    described_certificate__certificate_type__sid: str = None
    described_certificate__sid: str = None
    description: str = None


class NewCertificateDescriptionPeriodParser(NewWritable, NewElementParser):
    handler = CertificateDescriptionPeriodHandler
    record_code = "205"
    subrecord_code = "05"

    xml_object_tag = "certificate.description.period"

    sid: str = None
    described_certificate__certificate_type__sid: str = None
    described_certificate__sid: str = None
    validity_start: date = None
