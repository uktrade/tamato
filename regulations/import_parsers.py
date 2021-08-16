from importer.namespaces import Tag
from importer.parsers import BooleanElement
from importer.parsers import CompoundElement
from importer.parsers import ConstantElement
from importer.parsers import ElementParser
from importer.parsers import IntElement
from importer.parsers import TextElement
from importer.parsers import ValidityMixin
from importer.parsers import Writable
from importer.taric import RecordParser


@RecordParser.register_child("regulation_group")
class RegulationGroupParser(ValidityMixin, Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

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

    record_code = "150"
    subrecord_code = "00"

    tag = Tag(name="regulation.group")

    group_id = TextElement(Tag(name="regulation.group.id"))
    valid_between_lower = ValidityMixin.valid_between_lower
    valid_between_upper = ValidityMixin.valid_between_upper


@RecordParser.register_child("regulation_group_description")
class RegulationGroupDescriptionParser(Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

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

    record_code = "150"
    subrecord_code = "05"

    tag = Tag(name="regulation.group.description")

    group_id = TextElement(Tag(name="regulation.group.id"))
    language_id = ConstantElement(Tag(name="language.id"), value="EN")
    description = TextElement(Tag(name="description"))


@RecordParser.register_child("base_regulation")
class BaseRegulationParser(ValidityMixin, Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

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

    record_code = "285"
    subrecord_code = "00"

    tag = Tag(name="base.regulation")

    role_type = IntElement(Tag(name="base.regulation.role"))
    regulation_id = TextElement(Tag(name="base.regulation.id"))
    published_at = TextElement(Tag(name="published.date"))
    official_journal_number = TextElement(Tag(name="officialjournal.number"))
    official_journal_page = IntElement(Tag(name="officialjournal.page"))
    valid_between_lower = ValidityMixin.valid_between_lower
    valid_between_upper = ValidityMixin.valid_between_upper
    effective_end_date = TextElement(Tag(name="effective.end.date"))
    community_code = IntElement(Tag(name="community.code"))
    regulation_group__group_id = TextElement(Tag(name="regulation.group.id"))
    replacement_indicator = IntElement(Tag(name="replacement.indicator"))
    stopped = BooleanElement(Tag(name="stopped.flag"))
    information_text = CompoundElement(
        Tag(name="information.text"),
        "public_identifier",
        "url",
    )
    approved = BooleanElement(Tag(name="approved.flag"))


@RecordParser.register_child("modification_regulation")
class ModificationRegulationParser(ValidityMixin, Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

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

    record_code = "290"
    subrecord_code = "00"

    tag = Tag(name="modification.regulation")

    role_type = IntElement(Tag(name="modification.regulation.role"))
    regulation_id = TextElement(Tag(name="modification.regulation.id"))
    published_at = TextElement(Tag(name="published.date"))
    official_journal_number = TextElement(Tag(name="officialjournal.number"))
    official_journal_page = IntElement(Tag(name="officialjournal.page"))
    valid_between_lower = ValidityMixin.valid_between_lower
    valid_between_upper = ValidityMixin.valid_between_upper
    effective_end_date = TextElement(Tag(name="effective.end.date"))
    target_regulation__role_type = TextElement(Tag(name="base.regulation.role"))
    target_regulation__regulation_id = TextElement(Tag(name="base.regulation.id"))
    replacement_indicator = IntElement(Tag(name="replacement.indicator"))
    stopped = BooleanElement(Tag(name="stopped.flag"))
    information_text = CompoundElement(
        Tag(name="information.text"),
        "public_identifier",
        "url",
    )
    approved = BooleanElement(Tag(name="approved.flag"))


@RecordParser.register_child("fts_regulation")
class FullTemporaryStopRegulationParser(ValidityMixin, Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

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

    record_code = "300"
    subrecord_code = "00"

    tag = Tag(name="full.temporary.stop.regulation")

    role_type = IntElement(Tag(name="full.temporary.stop.regulation.role"))
    regulation_id = TextElement(Tag(name="full.temporary.stop.regulation.id"))
    published_at = TextElement(Tag(name="published.date"))
    official_journal_number = TextElement(Tag(name="officialjournal.number"))
    official_journal_page = IntElement(Tag(name="officialjournal.page"))
    valid_between_lower = ValidityMixin.valid_between_lower
    valid_between_upper = ValidityMixin.valid_between_upper
    effective_end_date = TextElement(Tag(name="effective.enddate"))
    replacement_indicator = IntElement(Tag(name="replacement.indicator"))
    information_text = CompoundElement(
        Tag(name="information.text"),
        "public_identifier",
        "url",
    )
    approved = BooleanElement(Tag(name="approved.flag"))


@RecordParser.register_child("fts_action")
class FullTemporaryStopActionParser(Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

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

    record_code = "305"
    subrecord_code = "00"

    tag = Tag(name="fts.regulation.action")

    role_type = IntElement(Tag(name="fts.regulation.role"))
    regulation_id = TextElement(Tag(name="fts.regulation.id"))
    target_regulation__role_type = IntElement(Tag(name="stopped.regulation.role"))
    target_regulation__regulation_id = TextElement(Tag(name="stopped.regulation.id"))


@RecordParser.register_child("regulation_replacement")
class RegulationReplacementParser(Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

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

    record_code = "305"
    subrecord_code = "00"

    tag = Tag(name="regulation.replacement")

    enacting_regulation__role_type = IntElement(Tag(name="replacing.regulation.role"))
    enacting_regulation__regulation_id = TextElement(
        Tag(name="replacing.regulation.id"),
    )
    target_regulation__role_type = IntElement(Tag(name="replaced.regulation.role"))
    target_regulation__regulation_id = TextElement(Tag(name="replaced.regulation.id"))
    measure_type_id = TextElement(Tag(name="measure.type.id"))
    geographical_area_id = TextElement(Tag(name="geographical.area.id"))
    chapter_heading = TextElement(Tag(name="chapter.heading"))
