from datetime import date

from importer.new_parsers import ModelLink
from importer.new_parsers import ModelLinkField
from importer.new_parsers import NewElementParser
from importer.parsers import NewValidityMixin
from importer.parsers import NewWritable
from regulations.import_handlers import *


class NewRegulationGroupParser(NewValidityMixin, NewWritable, NewElementParser):
    model = models.Group

    record_code = "150"
    subrecord_code = "00"

    xml_object_tag = "regulation.group"

    model_links = []

    value_mapping = {
        "regulation_group_id": "group_id",
        "validity_start_date": "valid_between_lower",
        "validity_end_date": "valid_between_upper",
    }

    group_id: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None


class NewRegulationGroupDescriptionParser(NewWritable, NewElementParser):
    model = models.Group
    parent_parser = NewRegulationGroupParser

    model_links = [
        ModelLink(
            models.Group,
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

    group_id: str = None
    # language_id: str = None
    description: str = None


class NewBaseRegulationParser(NewValidityMixin, NewWritable, NewElementParser):
    model = models.Regulation

    model_links = [
        ModelLink(
            models.Group,
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


class NewModificationRegulationParser(NewValidityMixin, NewWritable, NewElementParser):
    model = models.Amendment

    record_code = "290"
    subrecord_code = "00"

    xml_object_tag = "modification.regulation"

    enacting_regulation__role_type: str = None
    enacting_regulation__regulation_id: str = None
    enacting_regulation__published_at: str = None
    enacting_regulation__official_journal_number: str = None
    enacting_regulation__official_journal_page: str = None
    enacting_regulation__valid_between_lower: date = None
    enacting_regulation__valid_between_upper: date = None
    enacting_regulation__effective_end_date: str = None
    target_regulation__role_type: str = None
    target_regulation__regulation_id: str = None
    enacting_regulation__replacement_indicator: str = None
    enacting_regulation__stopped: str = None
    enacting_regulation__information_text: str = None
    enacting_regulation__approved: str = None


class NewFullTemporaryStopRegulationParser(
    NewValidityMixin,
    NewWritable,
    NewElementParser,
):
    model = models.Suspension
    record_code = "300"
    subrecord_code = "00"

    xml_object_tag = "full.temporary.stop.regulation"

    enacting_regulation__role_type: str = None
    enacting_regulation__regulation_id: str = None
    enacting_regulation__published_at: str = None
    enacting_regulation__official_journal_number: str = None
    enacting_regulation__official_journal_page: str = None
    enacting_regulation__valid_between_lower: date = None
    enacting_regulation__valid_between_upper: date = None
    effective_end_date: str = None
    enacting_regulation__replacement_indicator: str = None
    enacting_regulation__information_text: str = None
    enacting_regulation__approved: str = None


class NewFullTemporaryStopActionParser(NewWritable, NewElementParser):
    model = models.Suspension

    record_code = "305"
    subrecord_code = "00"

    xml_object_tag = "fts.regulation.action"

    enacting_regulation__role_type: str = None
    enacting_regulation__regulation_id: str = None
    target_regulation__role_type: str = None
    target_regulation__regulation_id: str = None


class NewRegulationReplacementParser(NewWritable, NewElementParser):
    model = models.Replacement

    record_code = "305"
    subrecord_code = "00"

    xml_object_tag = "regulation.replacement"

    enacting_regulation__role_type: str = None
    enacting_regulation__regulation_id: str = None
    target_regulation__role_type: str = None
    target_regulation__regulation_id: str = None
    measure_type_id: str = None
    geographical_area_id: str = None
    chapter_heading: str = None
