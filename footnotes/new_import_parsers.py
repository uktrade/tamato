from datetime import date

from footnotes.import_handlers import *
from importer.new_parsers import ModelLink
from importer.new_parsers import ModelLinkField
from importer.new_parsers import NewElementParser
from importer.parsers import NewChildPeriod
from importer.parsers import NewValidityMixin
from importer.parsers import NewWritable


class NewFootnoteTypeParser(NewValidityMixin, NewWritable, NewElementParser):
    model = models.FootnoteType

    model_links = []

    value_mapping = {
        "validity_start_date": "valid_between_lower",
        "validity_end_date": "valid_between_upper",
    }

    record_code = "100"
    subrecord_code = "00"

    xml_object_tag = "footnote.type"

    footnote_type_id: str = None
    valid_between_lower: str = None
    valid_between_upper: str = None
    application_code: str = None


class NewFootnoteTypeDescriptionParser(NewWritable, NewElementParser):
    model = models.FootnoteType
    model_links = [
        ModelLink(
            models.FootnoteType,
            [
                ModelLinkField("footnote_type_id", "footnote_type_id"),
            ],
            "footnote.type",
        ),
    ]

    record_code = "100"
    subrecord_code = "05"

    xml_object_tag = "footnote.type.description"

    footnote_type_id: str = None
    # language_id: str = None
    description: str = None


class NewFootnoteParser(NewValidityMixin, NewWritable, NewElementParser):
    model = models.Footnote

    model_links = [
        ModelLink(
            models.FootnoteType,
            [
                ModelLinkField("footnote_type_id", "footnote_type_id"),
            ],
            "footnote.type",
        ),
    ]

    value_mapping = {
        "validity_start_date": "valid_between_lower",
        "validity_end_date": "valid_between_upper",
    }

    record_code = "200"
    subrecord_code = "00"

    xml_object_tag = "footnote"

    footnote_type_id: str = None
    footnote_id: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None


class NewFootnoteDescriptionParser(NewWritable, NewElementParser):
    model = models.FootnoteDescription

    model_links = [
        ModelLink(
            models.Footnote,
            [
                ModelLinkField("described_footnote__footnote_id", "footnote_id"),
            ],
            "footnote",
        ),
        ModelLink(
            models.FootnoteType,
            [
                ModelLinkField(
                    "described_footnote__footnote_type__footnote_type_id",
                    "footnote_type_id",
                ),
            ],
            "footnote.type",
        ),
    ]

    record_code = "200"
    subrecord_code = "10"

    xml_object_tag = "footnote.description"

    sid: str = None
    # language_id: str = None
    described_footnote__footnote_type__footnote_type_id: str = None
    described_footnote__footnote_id: str = None
    description: str = None


class NewFootnoteDescriptionPeriodParser(NewWritable, NewElementParser, NewChildPeriod):
    model = models.FootnoteDescription
    parent_parser = NewFootnoteDescriptionParser

    model_links = [
        ModelLink(
            models.Footnote,
            [
                ModelLinkField("described_footnote__footnote_id", "footnote_id"),
            ],
            "footnote",
        ),
        ModelLink(
            models.FootnoteType,
            [
                ModelLinkField(
                    "described_footnote__footnote_type__footnote_type_id",
                    "footnote_type_id",
                ),
            ],
            "footnote.type",
        ),
        ModelLink(
            models.FootnoteDescription,
            [
                ModelLinkField(
                    "footnote_description_period__sid",
                    "sid",
                ),
            ],
            "footnote.description",
        ),
    ]

    value_mapping = {
        "footnote_description_period__sid": "sid",
    }

    record_code = "200"
    subrecord_code = "05"

    xml_object_tag = "footnote.description.period"

    sid: str = None
    described_footnote__footnote_type__footnote_type_id: str = None
    described_footnote__footnote_id: str = None
    validity_start: date = None
