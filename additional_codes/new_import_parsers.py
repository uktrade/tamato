from datetime import date

import additional_codes.models
from additional_codes.import_handlers import *
from footnotes.models import Footnote
from importer.new_parsers import ModelLink
from importer.new_parsers import ModelLinkField
from importer.new_parsers import NewElementParser
from importer.parsers import NewChildPeriod
from importer.parsers import NewValidityMixin
from importer.parsers import NewWritable


class NewAdditionalCodeTypeParser(NewValidityMixin, NewWritable, NewElementParser):
    model = additional_codes.models.AdditionalCodeType
    model_links = []

    value_mapping = {
        # "certificate_type_code": "certificate_type_sid",
        "additional_code_type_id": "sid",
        "validity_start_date": "valid_between_lower",
        "validity_end_date": "valid_between_upper",
    }

    record_code = "120"
    subrecord_code = "00"

    xml_object_tag = "additional.code.type"

    identity_fields = ["sid"]

    sid: int = None
    valid_between_lower: date = None
    valid_between_upper: date = None
    application_code: str = None


# This gets joined to AdditionalCodeType as description column
class NewAdditionalCodeTypeDescriptionParser(NewWritable, NewElementParser):
    model = models.AdditionalCodeType
    parent_parser = NewAdditionalCodeTypeParser

    model_links = [
        ModelLink(
            models.AdditionalCodeType,
            [
                ModelLinkField("sid", "sid"),
            ],
            "additional.code.type",
        ),
    ]

    value_mapping = {
        "additional_code_type_id": "sid",
    }

    record_code = "120"
    subrecord_code = "05"

    xml_object_tag = "additional.code.type.description"

    identity_fields = ["sid"]

    sid: int = None
    description: str = None


class NewAdditionalCodeParser(NewWritable, NewElementParser):
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

    value_mapping = {
        "additional_code": "code",
        "additional_code_sid": "sid",
        "additional_code_type_id": "type__sid",
        "validity_start_date": "valid_between_lower",
        "validity_end_date": "valid_between_upper",
    }

    record_code = "245"
    subrecord_code = "00"

    xml_object_tag = "additional.code"

    identity_fields = ["sid"]

    sid: int = None
    type__sid: int = None
    code: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None


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

    value_mapping = {
        "additional_code_description_period_sid": "sid",
        "additional_code_sid": "described_additionalcode__sid",
        "additional_code_type_id": "described_additionalcode__type__sid",
        "additional_code": "described_additionalcode__code",
        "validity_start_date": "validity_start",
    }

    record_code = "245"
    subrecord_code = "10"

    xml_object_tag = "additional.code.description"

    identity_fields = ["sid"]

    sid: int = None
    # language_id: str = None
    described_additionalcode__sid: int = None
    described_additionalcode__type__sid: int = None
    described_additionalcode__code: str = None
    description: str = None
    validity_start: date = None


class NewAdditionalCodeDescriptionPeriodParser(
    NewWritable,
    NewElementParser,
    NewChildPeriod,
):
    model = models.AdditionalCodeDescription
    parent_parser = NewAdditionalCodeDescriptionParser

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
        ModelLink(
            models.AdditionalCodeDescription,
            [
                ModelLinkField("sid", "sid"),
            ],
            "additional.code.description",
        ),
    ]

    value_mapping = {
        "additional_code_description_period_sid": "sid",
        "additional_code_sid": "described_additionalcode__sid",
        "additional_code_type_id": "described_additionalcode__type__sid",
        "additional_code": "described_additionalcode__code",
        "validity_start_date": "validity_start",
    }

    record_code = "245"
    subrecord_code = "05"

    xml_object_tag = "additional.code.description.period"

    identity_fields = ["sid"]

    sid: int = None
    described_additionalcode__sid: int = None
    described_additionalcode__type__sid: int = None
    described_additionalcode__code: str = None
    validity_start: date = None


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
                ModelLinkField(
                    "associated_footnote__footnote_type__footnote_type_id",
                    "footnote_type_id",
                ),
                ModelLinkField("associated_footnote__footnote_id", "footnote_id"),
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
                ModelLinkField("additional_code__sid", "sid"),
            ],
            "additional.code",
        ),
    ]

    value_mapping = {
        "additional_code_sid": "additional_code__sid",
        "footnote_type_id": "associated_footnote__footnote_type__footnote_type_id",
        "footnote_id": "associated_footnote__footnote_id",
        "additional_code_type_id": "additional_code__type__sid",
        "additional_code": "additional_code__code",
        "validity_start_date": "valid_between_lower",
        "validity_end_date": "valid_between_upper",
    }

    record_code = "245"
    subrecord_code = "15"

    xml_object_tag = "footnote.association.additional.code"

    identity_fields = []

    additional_code__sid: int = None
    associated_footnote__footnote_type__footnote_type_id: str = None
    associated_footnote__footnote_id: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None
    additional_code__type__sid: int = None
    additional_code__code: str = None
