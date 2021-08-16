from importer.namespaces import Tag
from importer.parsers import ConstantElement
from importer.parsers import ElementParser
from importer.parsers import IntElement
from importer.parsers import TextElement
from importer.parsers import ValidityMixin
from importer.parsers import ValidityStartMixin
from importer.parsers import Writable
from importer.taric import RecordParser


@RecordParser.register_child("additional_code")
class AdditionalCodeParser(ValidityMixin, Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="additional.code" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="additional.code.sid" type="SID"/>
                    <xs:element name="additional.code.type.id" type="AdditionalCodeTypeId"/>
                    <xs:element name="additional.code" type="AdditionalCode"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    record_code = "245"
    subrecord_code = "00"

    tag = Tag(name="additional.code")

    sid = IntElement(Tag(name="additional.code.sid"))
    type__sid = TextElement(Tag(name="additional.code.type.id"))
    code = TextElement(Tag(name="additional.code"))
    valid_between_lower = ValidityMixin.valid_between_lower
    valid_between_upper = ValidityMixin.valid_between_upper


@RecordParser.register_child("additional_code_description_period")
class AdditionalCodeDescriptionPeriodParser(
    ValidityStartMixin,
    Writable,
    ElementParser,
):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="additional.code.description.period" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="additional.code.description.period.sid" type="SID"/>
                    <xs:element name="additional.code.sid" type="SID"/>
                    <xs:element name="additional.code.type.id" type="AdditionalCodeTypeId"/>
                    <xs:element name="additional.code" type="AdditionalCode"/>
                    <xs:element name="validity.start.date" type="Date"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    record_code = "245"
    subrecord_code = "05"

    tag = Tag(name="additional.code.description.period")

    sid = TextElement(Tag(name="additional.code.description.period.sid"))
    described_additionalcode__sid = TextElement(Tag(name="additional.code.sid"))
    described_additionalcode__type__sid = TextElement(
        Tag(name="additional.code.type.id"),
    )
    described_additionalcode__code = TextElement(Tag(name="additional.code"))
    validity_start = ValidityStartMixin.validity_start


@RecordParser.register_child("additional_code_description")
class AdditionalCodeDescriptionParser(Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="additional.code.description" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="additional.code.description.period.sid" type="SID"/>
                    <xs:element name="language.id" type="LanguageId"/>
                    <xs:element name="additional.code.sid" type="SID"/>
                    <xs:element name="additional.code.type.id" type="AdditionalCodeTypeId"/>
                    <xs:element name="additional.code" type="AdditionalCode"/>
                    <xs:element name="description" type="LongDescription" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    record_code = "245"
    subrecord_code = "10"

    tag = Tag(name="additional.code.description")

    sid = TextElement(Tag(name="additional.code.description.period.sid"))
    language_id = ConstantElement(Tag(name="language.id"), value="EN")
    described_additionalcode__sid = TextElement(Tag(name="additional.code.sid"))
    described_additionalcode__type__sid = TextElement(
        Tag(name="additional.code.type.id"),
    )
    described_additionalcode__code = TextElement(Tag(name="additional.code"))
    description = TextElement(Tag(name="description"))


@RecordParser.register_child("additional_code_type")
class AdditionalCodeTypeParser(ValidityMixin, Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="additional.code.type" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="additional.code.type.id" type="AdditionalCodeTypeId"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                    <xs:element name="application.code" type="ApplicationCodeAdditionalCode"/>
                    <xs:element name="meursing.table.plan.id" type="MeursingTablePlanId" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    record_code = "120"
    subrecord_code = "00"

    tag = Tag(name="additional.code.type")

    sid = TextElement(Tag(name="additional.code.type.id"))
    valid_between_lower = ValidityMixin.valid_between_lower
    valid_between_upper = ValidityMixin.valid_between_upper
    application_code = TextElement(Tag(name="application.code"))


@RecordParser.register_child("additional_code_type_description")
class AdditionalCodeTypeDescriptionParser(Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="additional.code.type.description" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="additional.code.type.id" type="AdditionalCodeTypeId"/>
                    <xs:element name="language.id" type="LanguageId"/>
                    <xs:element name="description" type="ShortDescription" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    record_code = "120"
    subrecord_code = "05"

    tag = Tag(name="additional.code.type.description")

    sid = TextElement(Tag(name="additional.code.type.id"))
    language_id = ConstantElement(Tag(name="language.id"), value="EN")
    description = TextElement(Tag(name="description"))


@RecordParser.register_child("footnote_association_additional_code")
class FootnoteAssociationAdditionalCodeParser(ValidityMixin, Writable, ElementParser):
    """
    Example XML:

    .. code-block: XML

        <xs:element name="footnote.association.additional.code" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="additional.code.sid" type="SID"/>
                    <xs:element name="footnote.type.id" type="FootnoteTypeId"/>
                    <xs:element name="footnote.id" type="FootnoteId"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                    <xs:element name="additional.code.type.id" type="AdditionalCodeTypeId"/>
                    <xs:element name="additional.code" type="AdditionalCode"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    record_code = "245"
    subrecord_code = "15"

    tag = Tag(name="footnote.association.additional.code")

    additional_code__sid = TextElement(Tag(name="additional.code.sid"))
    associated_footnote__footnote_type__sid = TextElement(Tag(name="footnote.type.id"))
    associated_footnote__footnote_id = TextElement(Tag(name="footnote.id"))
    valid_between_lower = ValidityMixin.valid_between_lower
    valid_between_upper = ValidityMixin.valid_between_upper
    additional_code__type__sid = TextElement(Tag(name="additional.code.type.id"))
    additional_code__code = TextElement(Tag(name="additional.code"))
