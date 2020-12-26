from importer.namespaces import Tag
from importer.parsers import ElementParser
from importer.parsers import IntElement
from importer.parsers import TextElement
from importer.parsers import ValidityMixin
from importer.parsers import Writable
from importer.taric import RecordParser


@RecordParser.register_child("additional_code")
class AdditionalCodeParser(ValidityMixin, Writable, ElementParser):
    """
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

    tag = Tag("additional.code")

    sid = IntElement(Tag("additional.code.sid"))
    type__sid = TextElement(Tag("additional.code.type.id"))
    code = TextElement(Tag("additional.code"))
    valid_between_lower = TextElement(Tag("validity.start.date"))
    valid_between_upper = TextElement(Tag("validity.end.date"))


@RecordParser.register_child("additional_code_description_period")
class AdditionalCodeDescriptionPeriodParser(ValidityMixin, Writable, ElementParser):
    """
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

    tag = Tag("additional.code.description.period")

    description_period_sid = TextElement(Tag("additional.code.description.period.sid"))
    additional_code_sid = TextElement(Tag("additional.code.sid"))
    additional_code_type_id = TextElement(Tag("additional.code.type.id"))
    additional_code = TextElement(Tag("additional.code"))
    valid_between_lower = TextElement(Tag("validity.start.date"))


@RecordParser.register_child("additional_code_description")
class AdditionalCodeDescriptionParser(Writable, ElementParser):
    """
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

    tag = Tag("additional.code.description")

    description_period_sid = TextElement(Tag("additional.code.description.period.sid"))
    described_additional_code__sid = TextElement(Tag("additional.code.sid"))
    described_additional_code__type__sid = TextElement(Tag("additional.code.type.id"))
    described_additional_code__code = TextElement(Tag("additional.code"))
    description = TextElement(Tag("description"))


@RecordParser.register_child("additional_code_type")
class AdditionalCodeTypeParser(ValidityMixin, Writable, ElementParser):
    """
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

    tag = Tag("additional.code.type")

    sid = TextElement(Tag("additional.code.type.id"))
    application_code = TextElement(Tag("application.code"))
    valid_between_lower = TextElement(Tag("validity.start.date"))
    valid_between_upper = TextElement(Tag("validity.end.date"))


@RecordParser.register_child("additional_code_type_description")
class AdditionalCodeTypeDescriptionParser(ValidityMixin, Writable, ElementParser):
    """
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

    tag = Tag("additional.code.type.description")

    sid = TextElement(Tag("additional.code.type.id"))
    description = TextElement(Tag("description"))
