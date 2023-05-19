from datetime import date

import additional_codes.models
from additional_codes.import_handlers import *
from footnotes.models import Footnote
from importer.new_parsers import ModelLink
from importer.new_parsers import ModelLinkField
from importer.new_parsers import NewElementParser
from importer.parsers import NewValidityMixin
from importer.parsers import NewWritable


class NewAdditionalCodeTypeParser(NewValidityMixin, NewWritable, NewElementParser):
    model = additional_codes.models.AdditionalCodeType
    model_links = []

    record_code = "120"
    subrecord_code = "00"

    xml_object_tag = "additional.code.type"

    sid: str = None
    valid_between_lower: str = None
    valid_between_upper: str = None
    application_code: str = None


# This gets joined to AdditionalCodeType as description column
class NewAdditionalCodeTypeDescriptionParser(NewWritable, NewElementParser):
    model = additional_codes.models.AdditionalCodeType
    append_to_parent = True

    model_links = []

    record_code = "120"
    subrecord_code = "05"

    xml_object_tag = "additional.code.type.description"

    sid: str = None
    language_id: str = None
    description: str = None


class NewAdditionalCodeParser(NewValidityMixin, NewWritable, NewElementParser):
    model = additional_codes.models.AdditionalCode

    # create dependency to QuotaDefinition
    model_links = [
        ModelLink(
            models.AdditionalCodeType,
            [
                ModelLinkField("type__sid", "sid"),
            ],
            "additional.code.type",
        ),
    ]

    record_code = "245"
    subrecord_code = "00"

    xml_object_tag = "additional.code"

    sid: str = None
    type__sid: str = None
    code: str = None
    valid_between_lower: str = None
    valid_between_upper: str = None


class NewAdditionalCodeDescriptionPeriodParser(NewWritable, NewElementParser):
    model = models.AdditionalCodeDescription
    append_to_parent = True

    model_links = [
        ModelLink(
            models.AdditionalCode,
            [
                ModelLinkField("described_additionalcode__sid", "sid"),
                ModelLinkField("described_additionalcode__code", "code"),
            ],
            "additional.code",
        ),
        ModelLink(
            models.AdditionalCodeType,
            [
                ModelLinkField("described_additionalcode__type__sid", "sid"),
            ],
            "additional.code.type",
        ),
    ]

    record_code = "245"
    subrecord_code = "05"

    xml_object_tag = "additional.code.description.period"

    sid: str = None
    described_additionalcode__sid: str = None
    described_additionalcode__type__sid: str = None
    described_additionalcode__code: str = None
    validity_start: date = None


class NewAdditionalCodeDescriptionParser(NewWritable, NewElementParser):
    model = additional_codes.models.AdditionalCodeDescription

    # create dependency to QuotaDefinition
    model_links = [
        ModelLink(
            models.AdditionalCode,
            [
                ModelLinkField("described_additionalcode__sid", "sid"),
                ModelLinkField("described_additionalcode__code", "code"),
            ],
            "additional.code",
        ),
        ModelLink(
            models.AdditionalCodeType,
            [
                ModelLinkField("described_additionalcode__type__sid", "sid"),
            ],
            "additional.code.type",
        ),
    ]

    record_code = "245"
    subrecord_code = "10"

    xml_object_tag = "additional.code.description"

    sid: str = None
    language_id: str = None
    described_additionalcode__sid: str = None
    described_additionalcode__type__sid: str = None
    described_additionalcode__code: str = None
    description: str = None


class NewFootnoteAssociationAdditionalCodeParser(
    NewValidityMixin,
    NewWritable,
    NewElementParser,
):
    model = additional_codes.models.FootnoteAssociationAdditionalCode

    model_links = [
        ModelLink(
            Footnote,
            [
                ModelLinkField("associated_footnote__footnote_type__sid", "sid"),
                ModelLinkField("associated_footnote__footnote_id", "code"),
            ],
            "footnote",
        ),
        ModelLink(
            models.AdditionalCodeType,
            [
                ModelLinkField("additional_code__type__sid", "sid"),
            ],
            "additional.code.type",
        ),
        ModelLink(
            models.AdditionalCode,
            [
                ModelLinkField("additional_code__code", "code"),
            ],
            "additional.code",
        ),
    ]

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
