import logging

from importer.namespaces import Tag
from importer.parsers import ConstantElement
from importer.parsers import ElementParser
from importer.parsers import IntElement
from importer.parsers import TextElement
from importer.parsers import ValidityMixin
from importer.parsers import ValidityStartMixin
from importer.parsers import Writable
from importer.taric import RecordParser

logger = logging.getLogger(__name__)


@RecordParser.register_child("footnote_type")
class FootnoteTypeParser(ValidityMixin, Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

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

    record_code = "100"
    subrecord_code = "00"

    tag = Tag(name="footnote.type")

    footnote_type_id = TextElement(Tag(name="footnote.type.id"))
    valid_between_lower = ValidityMixin.valid_between_lower
    valid_between_upper = ValidityMixin.valid_between_upper
    application_code = TextElement(Tag(name="application.code"))


@RecordParser.register_child("footnote_type_description")
class FootnoteTypeDescriptionParser(Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

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

    record_code = "100"
    subrecord_code = "05"

    tag = Tag(name="footnote.type.description")

    footnote_type_id = TextElement(Tag(name="footnote.type.id"))
    language_id = ConstantElement(Tag(name="language.id"), value="EN")
    description = TextElement(Tag(name="description"))


@RecordParser.register_child("footnote")
class FootnoteParser(ValidityMixin, Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

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

    record_code = "200"
    subrecord_code = "00"

    tag = Tag(name="footnote")

    footnote_type__footnote_type_id = TextElement(Tag(name="footnote.type.id"))
    footnote_id = TextElement(Tag(name="footnote.id"))
    valid_between_lower = ValidityMixin.valid_between_lower
    valid_between_upper = ValidityMixin.valid_between_upper


@RecordParser.register_child("footnote_description")
class FootnoteDescriptionParser(Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

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

    record_code = "200"
    subrecord_code = "10"

    tag = Tag(name="footnote.description")

    sid = IntElement(Tag(name="footnote.description.period.sid"))
    language_id = ConstantElement(Tag(name="language.id"), value="EN")
    described_footnote__footnote_type__footnote_type_id = TextElement(
        Tag(name="footnote.type.id"),
    )
    described_footnote__footnote_id = TextElement(Tag(name="footnote.id"))
    description = TextElement(Tag(name="description"))


@RecordParser.register_child("footnote_description_period")
class FootnoteDescriptionPeriodParser(ValidityStartMixin, Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

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

    record_code = "200"
    subrecord_code = "05"

    tag = Tag(name="footnote.description.period")

    sid = IntElement(Tag(name="footnote.description.period.sid"))
    described_footnote__footnote_type__footnote_type_id = TextElement(
        Tag(name="footnote.type.id"),
    )
    described_footnote__footnote_id = TextElement(Tag(name="footnote.id"))
    validity_start = ValidityStartMixin.validity_start
