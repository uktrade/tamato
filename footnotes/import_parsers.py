import logging

from importer.namespaces import Tag
from importer.parsers import ElementParser
from importer.parsers import IntElement
from importer.parsers import TextElement
from importer.parsers import ValidityMixin
from importer.parsers import Writable
from importer.taric import Record


logger = logging.getLogger(__name__)


@Record.register_child("footnote_type")
class FootnoteTypeParser(ValidityMixin, Writable, ElementParser):
    """
    <xs:element name="footnote.type" substitutionGroup="abstract.record">
        <xs:complexType>
            <xs:sequence>
                <xs:element name="footnote.type.id" type="FootnoteTypeId"/>
                <xs:element name="validity.start.date" type="Date"/>
                <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                <xs:element name="application.code" type="ApplicationCodeFootnote"/>
            </xs:sequence>
        </xs:complexType>
    </xs:element>
    """

    tag = Tag("footnote.type")

    footnote_type_id = TextElement(Tag("footnote.type.id"))
    valid_between_lower = TextElement(Tag("validity.start.date"))
    valid_between_upper = TextElement(Tag("validity.end.date"))
    application_code = TextElement(Tag("application.code"))


@Record.register_child("footnote_type_description")
class FootnoteTypeDescriptionParser(ValidityMixin, Writable, ElementParser):
    """
    <xs:element name="footnote.type.description" substitutionGroup="abstract.record">
        <xs:complexType>
            <xs:sequence>
                <xs:element name="footnote.type.id" type="FootnoteTypeId"/>
                <xs:element name="language.id" type="LanguageId"/>
                <xs:element name="description" type="ShortDescription" minOccurs="0"/>
            </xs:sequence>
        </xs:complexType>
    </xs:element>
    """

    tag = Tag("footnote.type.description")

    footnote_type_id = TextElement(Tag("footnote.type.id"))
    description = TextElement(Tag("description"))


@Record.register_child("footnote")
class FootnoteParser(ValidityMixin, Writable, ElementParser):
    """
    <xs:element name="footnote" substitutionGroup="abstract.record">
        <xs:complexType>
            <xs:sequence>
                <xs:element name="footnote.type.id" type="FootnoteTypeId"/>
                <xs:element name="footnote.id" type="FootnoteId"/>
                <xs:element name="validity.start.date" type="Date"/>
                <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
            </xs:sequence>
        </xs:complexType>
    </xs:element>
    """

    tag = Tag("footnote")

    footnote_type__footnote_type_id = TextElement(Tag("footnote.type.id"))
    footnote_id = TextElement(Tag("footnote.id"))


@Record.register_child("footnote_description")
class FootnoteDescriptionParser(ValidityMixin, Writable, ElementParser):
    """
    <xs:element name="footnote.description" substitutionGroup="abstract.record">
        <xs:complexType>
            <xs:sequence>
                <xs:element name="footnote.description.period.sid" type="SID"/>
                <xs:element name="language.id" type="LanguageId"/>
                <xs:element name="footnote.type.id" type="FootnoteTypeId"/>
                <xs:element name="footnote.id" type="FootnoteId"/>
                <xs:element name="description" type="LongDescription" minOccurs="0"/>
            </xs:sequence>
        </xs:complexType>
    </xs:element>
    """

    tag = Tag("footnote.description")

    description_period_sid = IntElement(Tag("footnote.description.period.sid"))
    described_footnote__footnote_type__footnote_type_id = TextElement(
        Tag("footnote.type.id")
    )
    described_footnote__footnote_id = TextElement(Tag("footnote.id"))
    description = TextElement(Tag("description"))


@Record.register_child("footnote_description_period")
class FootnoteDescriptionPeriodParser(ValidityMixin, Writable, ElementParser):
    """
    <xs:element name="footnote.description.period" substitutionGroup="abstract.record">
        <xs:complexType>
            <xs:sequence>
                <xs:element name="footnote.description.period.sid" type="SID"/>
                <xs:element name="footnote.type.id" type="FootnoteTypeId"/>
                <xs:element name="footnote.id" type="FootnoteId"/>
                <xs:element name="validity.start.date" type="Date"/>
            </xs:sequence>
        </xs:complexType>
    </xs:element>
    """

    tag = Tag("footnote.description.period")

    description_period_sid = IntElement(Tag("footnote.description.period.sid"))
    described_footnote__footnote_type__footnote_type_id = TextElement(
        Tag("footnote.type.id")
    )
    described_footnote__footnote_id = TextElement(Tag("footnote.id"))
