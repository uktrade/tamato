from datetime import date

from regulations.models import Amendment
from regulations.models import Group
from regulations.models import Regulation
from regulations.models import Replacement
from regulations.models import Suspension
from taric_parsers.parser_model_link import ModelLink
from taric_parsers.parser_model_link import ModelLinkField
from taric_parsers.parsers.mixins import ValidityMixin
from taric_parsers.parsers.mixins import Writable
from taric_parsers.parsers.taric_parser import BaseTaricParser


class RegulationGroupParserV2(ValidityMixin, Writable, BaseTaricParser):
    model = Group

    record_code = "150"
    subrecord_code = "00"

    xml_object_tag = "regulation.group"

    model_links = []

    value_mapping = {
        "regulation_group_id": "group_id",
        "validity_start_date": "valid_between_lower",
        "validity_end_date": "valid_between_upper",
    }

    identity_fields = [
        "group_id",
    ]

    allow_update_without_children = True

    group_id: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None


class RegulationGroupDescriptionParserV2(Writable, BaseTaricParser):
    model = Group
    parent_parser = RegulationGroupParserV2

    model_links = [
        ModelLink(
            Group,
            [
                ModelLinkField("group_id", "group_id"),
            ],
            "group",
        ),
    ]

    value_mapping = {
        "regulation_group_id": "group_id",
    }

    record_code = "150"
    subrecord_code = "05"

    xml_object_tag = "regulation.group.description"

    identity_fields = [
        "group_id",
    ]

    deletes_allowed = False
    group_id: str = None
    description: str = None


class BaseRegulationParserV2(ValidityMixin, Writable, BaseTaricParser):
    model = Regulation

    model_links = [
        ModelLink(
            Group,
            [
                ModelLinkField("regulation_group__group_id", "group_id"),
            ],
            "group",
        ),
    ]

    value_mapping = {
        "officialjournal_number": "official_journal_number",
        "officialjournal_page": "official_journal_page",
        "published_date": "published_at",
        "base_regulation_id": "regulation_id",
        "base_regulation_role": "role_type",
        "regulation_group_id": "regulation_group__group_id",
        "validity_start_date": "valid_between_lower",
        "validity_end_date": "valid_between_upper",
        "stopped_flag": "stopped",
        "approved_flag": "approved",
    }

    record_code = "285"
    subrecord_code = "00"

    xml_object_tag = "base.regulation"

    identity_fields = [
        "regulation_id",
        "role_type",
    ]

    role_type: int = None
    regulation_id: str = None
    published_at: date = None
    official_journal_number: str = None
    official_journal_page: int = None
    valid_between_lower: date = None
    valid_between_upper: date = None
    effective_end_date: date = None
    community_code: int = None
    regulation_group__group_id: str = None
    replacement_indicator: int = None
    stopped: bool = None
    information_text: str = None
    approved: bool = None


class ModificationRegulationParserV2(ValidityMixin, Writable, BaseTaricParser):
    model = Amendment

    record_code = "290"
    subrecord_code = "00"

    xml_object_tag = "modification.regulation"

    value_mapping = {
        "modification_regulation_role": "enacting_regulation__role_type",
        "modification_regulation_id": "enacting_regulation__regulation_id",
        "published_date": "enacting_regulation__published_at",
        "officialjournal_number": "enacting_regulation__official_journal_number",
        "officialjournal_page": "enacting_regulation__official_journal_page",
        "validity_start_date": "enacting_regulation__valid_between_lower",
        "validity_end_date": "enacting_regulation__valid_between_upper",
        "effective_end_date": "enacting_regulation__effective_end_date",
        "base_regulation_role": "target_regulation__role_type",
        "base_regulation_id": "target_regulation__regulation_id",
        "replacement_indicator": "enacting_regulation__replacement_indicator",
        "stopped_flag": "enacting_regulation__stopped",
        "information_text": "enacting_regulation__information_text",
        "approved_flag": "enacting_regulation__approved",
    }

    identity_fields = [
        "enacting_regulation__role_type",
        "enacting_regulation__regulation_id",
        "target_regulation__regulation_id",
        "target_regulation__role_type",
    ]

    enacting_regulation__role_type: int = None
    enacting_regulation__regulation_id: str = None
    enacting_regulation__published_at: date = None
    enacting_regulation__official_journal_number: str = None
    enacting_regulation__official_journal_page: int = None
    enacting_regulation__valid_between_lower: date = None
    enacting_regulation__valid_between_upper: date = None
    enacting_regulation__effective_end_date: date = None
    target_regulation__role_type: int = None
    target_regulation__regulation_id: str = None
    enacting_regulation__replacement_indicator: int = None
    enacting_regulation__stopped: bool = None
    enacting_regulation__information_text: str = None
    enacting_regulation__approved: bool = None


class FullTemporaryStopRegulationParserV2(
    ValidityMixin,
    Writable,
    BaseTaricParser,
):
    """This handler creates both a base regulation with provided properties, and
    a suspension."""

    value_mapping = {
        "full_temporary_stop_regulation_role": "enacting_regulation__role_type",
        "full_temporary_stop_regulation_id": "enacting_regulation__regulation_id",
        "published_date": "enacting_regulation__published_at",
        "officialjournal_number": "enacting_regulation__official_journal_number",
        "officialjournal_page": "enacting_regulation__official_journal_page",
        "validity_start_date": "enacting_regulation__valid_between_lower",
        "validity_end_date": "enacting_regulation__valid_between_upper",
        "effective_enddate": "effective_end_date",
        "replacement_indicator": "enacting_regulation__replacement_indicator",
        "information_text": "enacting_regulation__information_text",
        "approved_flag": "enacting_regulation__approved",
    }

    model = Suspension
    record_code = "300"
    subrecord_code = "00"

    xml_object_tag = "full.temporary.stop.regulation"

    identity_fields = [
        "enacting_regulation__role_type",
        "enacting_regulation__regulation_id",
    ]

    enacting_regulation__role_type: int = None
    enacting_regulation__regulation_id: str = None
    enacting_regulation__published_at: date = None
    enacting_regulation__official_journal_number: str = None
    enacting_regulation__official_journal_page: int = None
    enacting_regulation__valid_between_lower: date = None
    enacting_regulation__valid_between_upper: date = None
    effective_end_date: date = None
    enacting_regulation__replacement_indicator: int = None
    enacting_regulation__information_text: str = None
    enacting_regulation__approved: bool = None


class FullTemporaryStopActionParserV2(Writable, BaseTaricParser):
    model = Suspension

    model_links = [
        ModelLink(
            Regulation,
            [
                ModelLinkField("enacting_regulation__role_type", "role_type"),
                ModelLinkField("enacting_regulation__regulation_id", "regulation_id"),
            ],
            "base.regulation",
        ),
        ModelLink(
            Regulation,
            [
                ModelLinkField("target_regulation__role_type", "role_type"),
                ModelLinkField("target_regulation__regulation_id", "regulation_id"),
            ],
            "base.regulation",
        ),
    ]

    value_mapping = {
        "fts_regulation_role": "enacting_regulation__role_type",
        "fts_regulation_id": "enacting_regulation__regulation_id",
        "stopped_regulation_role": "target_regulation__role_type",
        "stopped_regulation_id": "target_regulation__regulation_id",
    }

    record_code = "305"
    subrecord_code = "00"

    xml_object_tag = "fts.regulation.action"

    identity_fields = [
        "enacting_regulation__role_type",
        "enacting_regulation__regulation_id",
        "target_regulation__regulation_id",
        "target_regulation__role_type",
    ]

    enacting_regulation__role_type: str = None
    enacting_regulation__regulation_id: str = None
    target_regulation__role_type: str = None
    target_regulation__regulation_id: str = None


class RegulationReplacementParserV2(Writable, BaseTaricParser):
    model = Replacement

    model_links = [
        ModelLink(
            Regulation,
            [
                ModelLinkField("enacting_regulation__role_type", "role_type"),
                ModelLinkField("enacting_regulation__regulation_id", "regulation_id"),
            ],
            "base.regulation",
        ),
        ModelLink(
            Regulation,
            [
                ModelLinkField("target_regulation__role_type", "role_type"),
                ModelLinkField("target_regulation__regulation_id", "regulation_id"),
            ],
            "base.regulation",
        ),
    ]

    value_mapping = {
        "replacing_regulation_role": "enacting_regulation__role_type",
        "replacing_regulation_id": "enacting_regulation__regulation_id",
        "replaced_regulation_role": "target_regulation__role_type",
        "replaced_regulation_id": "target_regulation__regulation_id",
    }

    record_code = "305"
    subrecord_code = "00"

    xml_object_tag = "regulation.replacement"

    identity_fields = [
        "enacting_regulation__role_type",
        "enacting_regulation__regulation_id",
        "target_regulation__regulation_id",
        "target_regulation__role_type",
    ]

    enacting_regulation__role_type: int = None
    enacting_regulation__regulation_id: str = None
    target_regulation__role_type: int = None
    target_regulation__regulation_id: str = None
    measure_type_id: str = None
    geographical_area_id: str = None
    chapter_heading: str = None
