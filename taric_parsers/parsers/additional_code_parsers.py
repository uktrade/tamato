from datetime import date

from additional_codes.models import AdditionalCode
from additional_codes.models import AdditionalCodeDescription
from additional_codes.models import AdditionalCodeType
from additional_codes.models import FootnoteAssociationAdditionalCode
from footnotes.models import Footnote
from taric_parsers.parser_model_link import ModelLink
from taric_parsers.parser_model_link import ModelLinkField
from taric_parsers.parsers.mixins import ChildPeriod
from taric_parsers.parsers.mixins import ValidityMixin
from taric_parsers.parsers.mixins import Writable
from taric_parsers.parsers.taric_parser import BaseTaricParser


class NewAdditionalCodeTypeParser(ValidityMixin, Writable, BaseTaricParser):
    model = AdditionalCodeType
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

    sid: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None
    application_code: str = None
    allow_update_without_children = True


# This gets joined to AdditionalCodeType as description column
class NewAdditionalCodeTypeDescriptionParser(Writable, BaseTaricParser):
    model = AdditionalCodeType
    parent_parser = NewAdditionalCodeTypeParser

    model_links = [
        ModelLink(
            AdditionalCodeType,
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

    deletes_allowed = False

    sid: str = None
    description: str = None


class NewAdditionalCodeParser(Writable, BaseTaricParser):
    model = AdditionalCode

    # create dependency to QuotaDefinition
    model_links = [
        ModelLink(
            AdditionalCodeType,
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
    type__sid: str = None
    code: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None


class NewAdditionalCodeDescriptionParser(Writable, BaseTaricParser):
    model = AdditionalCodeDescription

    # create dependency to QuotaDefinition
    model_links = [
        ModelLink(
            AdditionalCode,
            [
                ModelLinkField("described_additionalcode__sid", "sid"),
                ModelLinkField("described_additionalcode__code", "code"),
                ModelLinkField("described_additionalcode__type__sid", "type__sid"),
            ],
            "additional.code",
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

    identity_fields = [
        "described_additionalcode__sid",
        "described_additionalcode__type__sid",
        "described_additionalcode__code",
    ]

    sid: int = None
    # language_id: str = None
    described_additionalcode__sid: int = None
    described_additionalcode__type__sid: str = None
    described_additionalcode__code: str = None
    description: str = None
    validity_start: date = None
    allow_update_without_children = True


class NewAdditionalCodeDescriptionPeriodParser(
    Writable,
    BaseTaricParser,
    ChildPeriod,
):
    model = AdditionalCodeDescription
    parent_parser = NewAdditionalCodeDescriptionParser

    model_links = [
        ModelLink(
            AdditionalCode,
            [
                ModelLinkField("described_additionalcode__sid", "sid"),
                ModelLinkField("described_additionalcode__code", "code"),
                ModelLinkField("described_additionalcode__type__sid", "type__sid"),
            ],
            "additional.code",
        ),
        ModelLink(
            AdditionalCodeDescription,
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

    deletes_allowed = False

    sid: int = None
    described_additionalcode__sid: int = None
    described_additionalcode__type__sid: str = None
    described_additionalcode__code: str = None
    validity_start: date = None


class NewFootnoteAssociationAdditionalCodeParser(
    ValidityMixin,
    Writable,
    BaseTaricParser,
):
    model = FootnoteAssociationAdditionalCode

    model_links = [
        ModelLink(
            Footnote,
            [
                ModelLinkField(
                    "associated_footnote__footnote_type__footnote_type_id",
                    "footnote_type__footnote_type_id",
                ),
                ModelLinkField("associated_footnote__footnote_id", "footnote_id"),
            ],
            "footnote",
        ),
        ModelLink(
            AdditionalCodeType,
            [
                ModelLinkField("additional_code__type__sid", "sid"),
            ],
            "additional.code.type",
        ),
        ModelLink(
            AdditionalCode,
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

    identity_fields = [
        "additional_code__sid",
        "additional_code__code",
        "additional_code__type__sid",
        "associated_footnote__footnote_type__footnote_type_id",
        "associated_footnote__footnote_id",
    ]

    additional_code__sid: int = None
    additional_code__code: str = None
    additional_code__type__sid: str = None
    associated_footnote__footnote_type__footnote_type_id: int = None
    associated_footnote__footnote_id: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None
