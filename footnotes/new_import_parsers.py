from datetime import date

from footnotes.import_handlers import *
from importer.new_parsers import NewElementParser
from importer.parsers import NewValidityMixin
from importer.parsers import NewWritable


class NewFootnoteTypeParser(NewValidityMixin, NewWritable, NewElementParser):
    handler = FootnoteTypeHandler
    record_code = "100"
    subrecord_code = "00"

    xml_object_tag = "footnote.type"

    footnote_type_id: str = None
    valid_between_lower: str = None
    valid_between_upper: str = None
    application_code: str = None


class NewFootnoteTypeDescriptionParser(NewWritable, NewElementParser):
    handler = FootnoteTypeDescriptionHandler

    record_code = "100"
    subrecord_code = "05"

    xml_object_tag = "footnote.type.description"

    footnote_type_id: str = None
    language_id: str = None
    description: str = None


class NewFootnoteParser(NewValidityMixin, NewWritable, NewElementParser):
    handler = FootnoteHandler

    record_code = "200"
    subrecord_code = "00"

    xml_object_tag = "footnote"

    footnote_type__footnote_type_id: str = None
    footnote_id: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None


class NewFootnoteDescriptionParser(NewWritable, NewElementParser):
    handler = FootnoteDescriptionHandler

    record_code = "200"
    subrecord_code = "10"

    xml_object_tag = "footnote.description"

    sid: str = None
    language_id: str = None
    described_footnote__footnote_type__footnote_type_id: str = None
    described_footnote__footnote_id: str = None
    description: str = None


class NewFootnoteDescriptionPeriodParser(NewWritable, NewElementParser):
    handler = FootnoteDescriptionPeriodHandler

    record_code = "200"
    subrecord_code = "05"

    xml_object_tag = "footnote.description.period"

    sid: str = None
    described_footnote__footnote_type__footnote_type_id: str = None
    described_footnote__footnote_id: str = None
    validity_start: date = None
