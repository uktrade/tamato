from datetime import date

from footnotes.models import Footnote
from footnotes.models import FootnoteDescription
from footnotes.models import FootnoteType
from taric_parsers.parser_model_link import ModelLink  # noqa
from taric_parsers.parser_model_link import ModelLinkField
from taric_parsers.parsers.mixins import ChildPeriod
from taric_parsers.parsers.mixins import ValidityMixin
from taric_parsers.parsers.mixins import Writable
from taric_parsers.parsers.taric_parser import BaseTaricParser


class FootnoteTypeParserV2(Writable, BaseTaricParser):
    model = FootnoteType

    model_links = []

    value_mapping = {
        "validity_start_date": "valid_between_lower",
        "validity_end_date": "valid_between_upper",
    }

    record_code = "100"
    subrecord_code = "00"

    xml_object_tag = "footnote.type"

    identity_fields = [
        "footnote_type_id",
    ]

    allow_update_without_children = True
    footnote_type_id: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None
    application_code: str = None


class FootnoteTypeDescriptionParserV2(Writable, BaseTaricParser):
    model = FootnoteType
    parent_parser = FootnoteTypeParserV2

    model_links = [
        ModelLink(
            FootnoteType,
            [
                ModelLinkField("footnote_type_id", "footnote_type_id"),
            ],
            "footnote.type",
        ),
    ]

    record_code = "100"
    subrecord_code = "05"

    xml_object_tag = "footnote.type.description"

    identity_fields = [
        "footnote_type_id",
    ]

    footnote_type_id: str = None
    # language_id: str = None
    description: str = None


class FootnoteParserV2(ValidityMixin, Writable, BaseTaricParser):
    model = Footnote

    model_links = [
        ModelLink(
            FootnoteType,
            [
                ModelLinkField("footnote_type__footnote_type_id", "footnote_type_id"),
            ],
            "footnote.type",
        ),
    ]

    value_mapping = {
        "validity_start_date": "valid_between_lower",
        "validity_end_date": "valid_between_upper",
        "footnote_type_id": "footnote_type__footnote_type_id",
    }

    record_code = "200"
    subrecord_code = "00"

    xml_object_tag = "footnote"

    identity_fields = [
        "footnote_id",
    ]

    footnote_type__footnote_type_id: str = None
    footnote_id: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None


class FootnoteDescriptionParserV2(Writable, BaseTaricParser):
    model = FootnoteDescription

    model_links = [
        ModelLink(
            Footnote,
            [
                ModelLinkField("described_footnote__footnote_id", "footnote_id"),
                ModelLinkField(
                    "described_footnote__footnote_type__footnote_type_id",
                    "footnote_type__footnote_type_id",
                ),
            ],
            "footnote",
        ),
    ]

    value_mapping = {
        "footnote_description_period_sid": "sid",
        "footnote_type_id": "described_footnote__footnote_type__footnote_type_id",
        "footnote_id": "described_footnote__footnote_id",
    }

    record_code = "200"
    subrecord_code = "10"

    xml_object_tag = "footnote.description"

    identity_fields = [
        "described_footnote__footnote_type__footnote_type_id",
        "described_footnote__footnote_id",
    ]

    allow_update_without_children = True

    sid: int = None
    described_footnote__footnote_type__footnote_type_id: str = None
    described_footnote__footnote_id: str = None
    description: str = None


class FootnoteDescriptionPeriodParserV2(Writable, BaseTaricParser, ChildPeriod):
    model = FootnoteDescription
    parent_parser = FootnoteDescriptionParserV2

    model_links = [
        ModelLink(
            Footnote,
            [
                ModelLinkField("described_footnote__footnote_id", "footnote_id"),
                ModelLinkField(
                    "described_footnote__footnote_type__footnote_type_id",
                    "footnote_type__footnote_type_id",
                ),
            ],
            "footnote",
        ),
        ModelLink(
            FootnoteDescription,
            [
                ModelLinkField("sid", "sid"),
            ],
            "footnote.description",
        ),
    ]

    value_mapping = {
        "footnote_description_period_sid": "sid",
        "footnote_type_id": "described_footnote__footnote_type__footnote_type_id",
        "footnote_id": "described_footnote__footnote_id",
        "validity_start_date": "validity_start",
    }

    record_code = "200"
    subrecord_code = "05"

    xml_object_tag = "footnote.description.period"

    identity_fields = [
        "sid",
    ]

    deletes_allowed = False

    sid: int = None
    described_footnote__footnote_type__footnote_type_id: str = None
    described_footnote__footnote_id: str = None
    validity_start: date = None
