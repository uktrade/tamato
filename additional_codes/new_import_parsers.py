from datetime import date

from importer.new_parsers import NewElementParser
from importer.parsers import NewValidityMixin
from importer.parsers import NewWritable


class NewAdditionalCodeParser(NewValidityMixin, NewWritable, NewElementParser):
    record_code = "245"
    subrecord_code = "00"

    xml_object_tag = "additional.code"

    sid: str = None
    type__sid: str = None
    code: str = None
    valid_between_lower: str = None
    valid_between_upper: str = None


class NewAdditionalCodeDescriptionPeriodParser(NewWritable, NewElementParser):
    record_code = "245"
    subrecord_code = "05"

    xml_object_tag = "additional.code.description.period"

    sid: str = None
    described_additionalcode__sid: str = None
    described_additionalcode__type__sid: str = None
    described_additionalcode__code: str = None
    validity_start: date = None


class NewAdditionalCodeDescriptionParser(NewWritable, NewElementParser):
    record_code = "245"
    subrecord_code = "10"

    xml_object_tag = "additional.code.description"

    sid: str = None
    language_id: str = None
    described_additionalcode__sid: str = None
    described_additionalcode__type__sid: str = None
    described_additionalcode__code: str = None
    description: str = None


class NewAdditionalCodeTypeParser(NewValidityMixin, NewWritable, NewElementParser):
    record_code = "120"
    subrecord_code = "00"

    xml_object_tag = "additional.code.type"

    sid: str = None
    valid_between_lower: str = None
    valid_between_upper: str = None
    application_code: str = None


class NewAdditionalCodeTypeDescriptionParser(NewWritable, NewElementParser):
    record_code = "120"
    subrecord_code = "05"

    xml_object_tag = "additional.code.type.description"

    sid: str = None
    language_id: str = None
    description: str = None


class NewFootnoteAssociationAdditionalCodeParser(
    NewValidityMixin,
    NewWritable,
    NewElementParser,
):
    record_code = "245"
    subrecord_code = "15"

    xml_object_tag = "footnote.association.additional.code"

    additional_code__sid: str = None
    associated_footnote__footnote_type__sid: str = None
    associated_footnote__footnote_id: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None
    additional_code__type__sid: str = None
    additional_code__code: str = None
