from importer.namespaces import Tag
from importer.parsers import ElementParser
from importer.parsers import TextElement
from importer.parsers import ValidityMixin
from importer.parsers import Writable


class CertificateTypeParser(ValidityMixin, Writable, ElementParser):
    tag = Tag("certificate.type")

    sid = TextElement(Tag("certificate.type.code"))
    valid_between_lower = TextElement(Tag("validity.start.date"))
    valid_between_upper = TextElement(Tag("validity.end.date"))


class CertificateTypeDescriptionParser(Writable, ElementParser):
    tag = Tag("certificate.type.description")

    sid = TextElement(Tag("certificate.type.code"))
    description = TextElement(Tag("description"))


class CertificateParser(ValidityMixin, Writable, ElementParser):
    tag = Tag("certificate")

    sid = TextElement(Tag("certificate.type.code"))


class CertificateDescriptionParser(Writable, ElementParser):
    tag = Tag("certificate.description")

    sid = TextElement(Tag("certificate.description.period.sid"))
    description = TextElement(Tag("description"))
    certificate_sid = TextElement(Tag("certificate.code"))
    certificate_type_sid = TextElement(Tag("certificate.code"))


class CertificateDescriptionPeriodParser(ValidityMixin, Writable, ElementParser):
    tag = Tag("certificate.description.period")

    sid = TextElement(Tag("certificate.description.period.sid"))
    valid_between_lower = TextElement(Tag("validity.start.date"))
    valid_between_upper = TextElement(Tag("validity.end.date"))
