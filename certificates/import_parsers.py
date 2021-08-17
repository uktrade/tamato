from importer.namespaces import Tag
from importer.parsers import ConstantElement
from importer.parsers import ElementParser
from importer.parsers import IntElement
from importer.parsers import TextElement
from importer.parsers import ValidityMixin
from importer.parsers import ValidityStartMixin
from importer.parsers import Writable
from importer.taric import RecordParser


@RecordParser.register_child("certificate_type")
class CertificateTypeParser(ValidityMixin, Writable, ElementParser):
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

    record_code = "110"
    subrecord_code = "00"

    tag = Tag("certificate.type")

    sid = TextElement(Tag("certificate.type.code"))
    valid_between_lower = ValidityMixin.valid_between_lower
    valid_between_upper = ValidityMixin.valid_between_upper


@RecordParser.register_child("certificate_type_description")
class CertificateTypeDescriptionParser(Writable, ElementParser):
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

    record_code = "110"
    subrecord_code = "05"

    tag = Tag("certificate.type.description")

    sid = TextElement(Tag("certificate.type.code"))
    language_id = ConstantElement(Tag("language.id"), value="EN")
    description = TextElement(Tag("description"))


@RecordParser.register_child("certificate")
class CertificateParser(ValidityMixin, Writable, ElementParser):
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

    record_code = "205"
    subrecord_code = "00"

    tag = Tag("certificate")

    certificate_type__sid = TextElement(Tag("certificate.type.code"))
    sid = TextElement(Tag("certificate.code"))
    valid_between_lower = ValidityMixin.valid_between_lower
    valid_between_upper = ValidityMixin.valid_between_upper


@RecordParser.register_child("certificate_description")
class CertificateDescriptionParser(Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="certificate.description" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="certificate.description.period.sid" type="SID"/>
                    <xs:element name="language.id" type="LanguageId"/>
                    <xs:element name="certificate.type.code" type="CertificateTypeCode"/>
                    <xs:element name="certificate.code" type="CertificateCode"/>
                    <xs:element name="description" type="ShortDescription" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    record_code = "205"
    subrecord_code = "10"

    tag = Tag("certificate.description")

    sid = IntElement(Tag("certificate.description.period.sid"))
    language_id = ConstantElement(Tag("language.id"), value="EN")
    described_certificate__certificate_type__sid = TextElement(
        Tag("certificate.type.code"),
    )
    described_certificate__sid = TextElement(Tag("certificate.code"))
    description = TextElement(Tag("description"))


@RecordParser.register_child("certificate_description_period")
class CertificateDescriptionPeriodParser(ValidityStartMixin, Writable, ElementParser):
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

    record_code = "205"
    subrecord_code = "05"

    tag = Tag("certificate.description.period")

    sid = IntElement(Tag("certificate.description.period.sid"))
    described_certificate__certificate_type__sid = TextElement(
        Tag("certificate.type.code"),
    )
    described_certificate__sid = TextElement(Tag("certificate.code"))
    validity_start = ValidityStartMixin.validity_start
