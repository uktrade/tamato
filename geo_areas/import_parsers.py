import logging

from importer.namespaces import Tag
from importer.parsers import ElementParser
from importer.parsers import IntElement
from importer.parsers import TextElement
from importer.parsers import ValidityMixin
from importer.parsers import Writable
from importer.taric import RecordParser


logger = logging.getLogger(__name__)


@RecordParser.register_child("geographical_area")
class GeographicalAreaParser(ValidityMixin, Writable, ElementParser):
    """
    <xs:element name="geographical.area" substitutionGroup="abstract.record">
        <xs:complexType>
            <xs:sequence>
                <xs:element name="geographical.area.sid" type="SID"/>
                <xs:element name="geographical.area.id" type="GeographicalAreaId"/>
                <xs:element name="validity.start.date" type="Date"/>
                <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                <xs:element name="geographical.code" type="AreaCode"/>
                <xs:element name="parent.geographical.area.group.sid" type="SID" minOccurs="0"/>
            </xs:sequence>
        </xs:complexType>
    </xs:element>
    """

    tag = Tag("geographical.area")

    sid = TextElement(Tag("geographical.area.sid"))
    area_id = TextElement(Tag("geographical.area.id"))
    area_code = TextElement(Tag("geographical.code"))
    parent__sid = TextElement(Tag("parent.geographical.area.group.sid"))


@RecordParser.register_child("geographical_area_description")
class GeographicalAreaDescriptionParser(Writable, ElementParser):
    """
    <xs:element name="geographical.area.description" substitutionGroup="abstract.record">
        <xs:complexType>
            <xs:sequence>
                <xs:element name="geographical.area.description.period.sid" type="SID"/>
                <xs:element name="language.id" type="LanguageId"/>
                <xs:element name="geographical.area.sid" type="SID"/>
                <xs:element name="geographical.area.id" type="GeographicalAreaId"/>
                <xs:element name="description" type="ShortDescription" minOccurs="0"/>
            </xs:sequence>
        </xs:complexType>
    </xs:element>
    """

    tag = Tag("geographical.area.description")

    sid = IntElement(Tag("geographical.area.description.period.sid"))
    area__sid = TextElement(Tag("geographical.area.sid"))
    area__area_id = TextElement(Tag("geographical.area.id"))
    description = TextElement(Tag("description"))


@RecordParser.register_child("geographical_area_description_period")
class GeographicalAreaDescriptionPeriodParser(ValidityMixin, Writable, ElementParser):
    """
    <xs:element name="geographical.area.description.period" substitutionGroup="abstract.record">
        <xs:complexType>
            <xs:sequence>
                <xs:element name="geographical.area.description.period.sid" type="SID"/>
                <xs:element name="geographical.area.sid" type="SID"/>
                <xs:element name="validity.start.date" type="Date"/>
                <xs:element name="geographical.area.id" type="GeographicalAreaId"/>
            </xs:sequence>
        </xs:complexType>
    </xs:element>
    """

    tag = Tag("geographical.area.description.period")

    sid = IntElement(Tag("geographical.area.description.period.sid"))
    area__sid = TextElement(Tag("geographical.area.sid"))
    area__area_id = TextElement(Tag("geographical.area.id"))


@RecordParser.register_child("geographical_area_membership")
class GeographicalAreaMembershipParser(ValidityMixin, Writable, ElementParser):
    """
    <xs:element name="geographical.area.membership" substitutionGroup="abstract.record">
        <xs:complexType>
            <xs:sequence>
                <xs:element name="geographical.area.sid" type="SID"/>
                <xs:element name="geographical.area.group.sid" type="SID"/>
                <xs:element name="validity.start.date" type="Date"/>
                <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
            </xs:sequence>
        </xs:complexType>
    </xs:element>
    """

    tag = Tag("geographical.area.membership")

    member__sid = IntElement(Tag("geographical.area.sid"))
    geo_group__sid = IntElement(Tag("geographical.area.group.sid"))
