from importer.namespaces import Tag
from importer.parsers import ElementParser
from importer.parsers import IntElement
from importer.parsers import TextElement
from importer.parsers import ValidityMixin
from importer.parsers import Writable
from importer.taric import Record


@Record.register_child("regulation_group")
class RegulationGroupParser(ValidityMixin, Writable, ElementParser):
    """
    <xs:element name="regulation.group" substitutionGroup="abstract.record">
        <xs:complexType>
            <xs:sequence>
                <xs:element name="regulation.group.id" type="RegulationGroupId"/>
                <xs:element name="validity.start.date" type="Date"/>
                <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
            </xs:sequence>
        </xs:complexType>
    </xs:element>
    """

    tag = Tag("regulation.group")

    group_id = TextElement(Tag("regulation.group.id"))


@Record.register_child("regulation_group_description")
class RegulationGroupDescriptionParser(Writable, ElementParser):
    """
    <xs:element name="regulation.group.description" substitutionGroup="abstract.record">
        <xs:complexType>
            <xs:sequence>
                <xs:element name="regulation.group.id" type="RegulationGroupId"/>
                <xs:element name="language.id" type="LanguageId"/>
                <xs:element name="description" type="ShortDescription" minOccurs="0"/>
            </xs:sequence>
        </xs:complexType>
    </xs:element>
    """

    tag = Tag("regulation.group.description")

    group_id = TextElement(Tag("regulation.group.id"))
    description = TextElement(Tag("description"))


@Record.register_child("base_regulation")
class BaseRegulationParser(ValidityMixin, Writable, ElementParser):
    """
    <xs:element name="base.regulation" substitutionGroup="abstract.record">
        <xs:complexType>
            <xs:sequence>
                <xs:element name="base.regulation.role" type="RegulationRoleTypeId"/>
                <xs:element name="base.regulation.id" type="RegulationId"/>
                <xs:element name="published.date" type="Date" minOccurs="0"/>
                <xs:element name="officialjournal.number" type="OfficialJournalNumber" minOccurs="0"/>
                <xs:element name="officialjournal.page" type="OfficialJournalPage" minOccurs="0"/>
                <xs:element name="validity.start.date" type="Date"/>
                <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                <xs:element name="effective.end.date" type="Date" minOccurs="0"/>
                <xs:element name="community.code" type="CommunityCode"/>
                <xs:element name="regulation.group.id" type="RegulationGroupId"/>
                <xs:element name="antidumping.regulation.role" type="RegulationRoleTypeId" minOccurs="0"/>
                <xs:element name="related.antidumping.regulation.id" type="RegulationId" minOccurs="0"/>
                <xs:element name="complete.abrogation.regulation.role" type="RegulationRoleTypeId" minOccurs="0"/>
                <xs:element name="complete.abrogation.regulation.id" type="RegulationId" minOccurs="0"/>
                <xs:element name="explicit.abrogation.regulation.role" type="RegulationRoleTypeId" minOccurs="0"/>
                <xs:element name="explicit.abrogation.regulation.id" type="RegulationId" minOccurs="0"/>
                <xs:element name="replacement.indicator" type="ReplacementIndicator"/>
                <xs:element name="stopped.flag" type="StoppedFlag"/>
                <xs:element name="information.text" type="ShortDescription" minOccurs="0"/>
                <xs:element name="approved.flag" type="ApprovedFlag"/>
            </xs:sequence>
        </xs:complexType>
    </xs:element>
    """

    tag = Tag("base.regulation")

    role_type = IntElement(Tag("base.regulation.role"))
    regulation_group__group_id = TextElement(Tag("regulation.group.id"))
    regulation_id = TextElement(Tag("base.regulation.id"))
    published_at = TextElement(Tag("published.date"))
    official_journal_number = TextElement(Tag("officialjournal.number"))
    official_journal_page = IntElement(Tag("officialjournal.page"))
    community_code = IntElement(Tag("community.code"))
    replacement_indicator = IntElement(Tag("replacement.indicator"))
    stopped = TextElement(Tag("stopped.flag"))
    information_text = TextElement(Tag("information.text"))
    approved = TextElement(Tag("approved.flag"))


@Record.register_child("modification_regulation")
class ModificationRegulationParser(ValidityMixin, Writable, ElementParser):
    """
    <xs:element name="modification.regulation" substitutionGroup="abstract.record">
        <xs:complexType>
            <xs:sequence>
                <xs:element name="modification.regulation.role" type="RegulationRoleTypeId"/>
                <xs:element name="modification.regulation.id" type="RegulationId"/>
                <xs:element name="published.date" type="Date" minOccurs="0"/>
                <xs:element name="officialjournal.number" type="OfficialJournalNumber" minOccurs="0"/>
                <xs:element name="officialjournal.page" type="OfficialJournalPage" minOccurs="0"/>
                <xs:element name="validity.start.date" type="Date"/>
                <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                <xs:element name="effective.end.date" type="Date" minOccurs="0"/>
                <xs:element name="base.regulation.role" type="RegulationRoleTypeId"/>
                <xs:element name="base.regulation.id" type="RegulationId"/>
                <xs:element name="complete.abrogation.regulation.role" type="RegulationRoleTypeId" minOccurs="0"/>
                <xs:element name="complete.abrogation.regulation.id" type="RegulationId" minOccurs="0"/>
                <xs:element name="explicit.abrogation.regulation.role" type="RegulationRoleTypeId" minOccurs="0"/>
                <xs:element name="explicit.abrogation.regulation.id" type="RegulationId" minOccurs="0"/>
                <xs:element name="replacement.indicator" type="ReplacementIndicator"/>
                <xs:element name="stopped.flag" type="StoppedFlag"/>
                <xs:element name="information.text" type="ShortDescription" minOccurs="0"/>
                <xs:element name="approved.flag" type="ApprovedFlag"/>
            </xs:sequence>
        </xs:complexType>
    </xs:element>
    """

    tag = Tag("modification.regulation")

    role_type = IntElement(Tag("modification.regulation.role"))
    regulation_id = TextElement(Tag("modification.regulation.id"))
    published_at = TextElement(Tag("published.date"))
    official_journal_number = TextElement(Tag("officialjournal.number"))
    official_journal_page = IntElement(Tag("officialjournal.page"))
    effective_end_date = TextElement(Tag("effective.end.date"))
    target_regulation__regulation_role = TextElement(Tag("base.regulation.role"))
    target_regulation__regulation_id = TextElement(Tag("base.regulation.id"))
    replacement_indicator = IntElement(Tag("replacement.indicator"))
    stopped = TextElement(Tag("stopped.flag"))
    information_text = TextElement(Tag("information.text"))
    approved = TextElement(Tag("approved.flag"))


@Record.register_child("fts_regulation")
class FullTemporaryStopRegulationParser(ValidityMixin, Writable, ElementParser):
    """
    <xs:element name="full.temporary.stop.regulation" substitutionGroup="abstract.record">
        <xs:complexType>
            <xs:sequence>
                <xs:element name="full.temporary.stop.regulation.role" type="RegulationRoleTypeId"/>
                <xs:element name="full.temporary.stop.regulation.id" type="RegulationId"/>
                <xs:element name="published.date" type="Date" minOccurs="0"/>
                <xs:element name="officialjournal.number" type="OfficialJournalNumber" minOccurs="0"/>
                <xs:element name="officialjournal.page" type="OfficialJournalPage" minOccurs="0"/>
                <xs:element name="validity.start.date" type="Date"/>
                <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                <xs:element name="effective.enddate" type="Date" minOccurs="0"/>
                <xs:element name="complete.abrogation.regulation.role" type="RegulationRoleTypeId" minOccurs="0"/>
                <xs:element name="complete.abrogation.regulation.id" type="RegulationId" minOccurs="0"/>
                <xs:element name="explicit.abrogation.regulation.role" type="RegulationRoleTypeId" minOccurs="0"/>
                <xs:element name="explicit.abrogation.regulation.id" type="RegulationId" minOccurs="0"/>
                <xs:element name="replacement.indicator" type="ReplacementIndicator"/>
                <xs:element name="information.text" type="ShortDescription" minOccurs="0"/>
                <xs:element name="approved.flag" type="ApprovedFlag"/>
            </xs:sequence>
        </xs:complexType>
    </xs:element>
    """

    tag = Tag("full.temporary.stop.regulation")

    role_type = IntElement(Tag("full.temporary.stop.regulation.role"))
    regulation_id = TextElement(Tag("full.temporary.stop.regulation.id"))
    published_at = TextElement(Tag("published.date"))
    official_journal_number = TextElement(Tag("officialjournal.number"))
    official_journal_page = IntElement(Tag("officialjournal.page"))
    effective_end_date = TextElement(Tag("effective.enddate"))
    replacement_indicator = IntElement(Tag("replacement.indicator"))
    information_text = TextElement(Tag("information.text"))
    approved = TextElement(Tag("approved.flag"))


@Record.register_child("fts_action")
class FullTemporaryStopActionParser(Writable, ElementParser):
    """
    <xs:element name="fts.regulation.action" substitutionGroup="abstract.record">
        <xs:complexType>
            <xs:sequence>
                <xs:element name="fts.regulation.role" type="RegulationRoleTypeId"/>
                <xs:element name="fts.regulation.id" type="RegulationId"/>
                <xs:element name="stopped.regulation.role" type="RegulationRoleTypeId"/>
                <xs:element name="stopped.regulation.id" type="RegulationId"/>
            </xs:sequence>
        </xs:complexType>
    </xs:element>
    """

    tag = Tag("fts.regulation.action")

    role_type = IntElement(Tag("fts.regulation.role"))
    regulation_id = TextElement(Tag("fts.regulation.id"))
    target_regulation__role_type = IntElement(Tag("stopped.regulation.role"))
    target_regulation__regulation_id = TextElement(Tag("stopped.regulation.id"))


@Record.register_child("regulation_replacement")
class RegulationReplacementParser(Writable, ElementParser):
    """
    <xs:element name="regulation.replacement" substitutionGroup="abstract.record">
        <xs:complexType>
            <xs:sequence>
                <xs:element name="replacing.regulation.role" type="RegulationRoleTypeId"/>
                <xs:element name="replacing.regulation.id" type="RegulationId"/>
                <xs:element name="replaced.regulation.role" type="RegulationRoleTypeId"/>
                <xs:element name="replaced.regulation.id" type="RegulationId"/>
                <xs:element name="measure.type.id" type="MeasureTypeId" minOccurs="0"/>
                <xs:element name="geographical.area.id" type="GeographicalAreaId" minOccurs="0"/>
                <xs:element name="chapter.heading" type="ChapterHeading" minOccurs="0"/>
            </xs:sequence>
        </xs:complexType>
    </xs:element>
    """

    tag = Tag("regulation.replacement")

    enacting_regulation__role_type = IntElement(Tag("replacing.regulation.role"))
    enacting_regulation__regulation_id = TextElement(Tag("replacing.regulation.id"))
    target_regulation__role_type = IntElement(Tag("replaced.regulation.role"))
    target_regulation__regulation_id = TextElement(Tag("replaced.regulation.id"))
    measure_type_id = TextElement(Tag("measure.type.id"))
    geographical_area_id = TextElement(Tag("geographical.area.id"))
    chapter_heading = TextElement(Tag("chapter.heading"))
