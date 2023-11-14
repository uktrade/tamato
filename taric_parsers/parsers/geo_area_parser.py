from datetime import date

from geo_areas.models import GeographicalArea
from geo_areas.models import GeographicalAreaDescription
from geo_areas.models import GeographicalMembership
from taric_parsers.parser_model_link import ModelLink
from taric_parsers.parser_model_link import ModelLinkField
from taric_parsers.parsers.mixins import ChildPeriod
from taric_parsers.parsers.mixins import ValidityMixin
from taric_parsers.parsers.mixins import Writable
from taric_parsers.parsers.taric_parser import BaseTaricParser


class NewGeographicalAreaParser(ValidityMixin, Writable, BaseTaricParser):
    model = GeographicalArea

    model_links = [
        ModelLink(
            GeographicalArea,
            [
                ModelLinkField("parent__sid", "sid"),
            ],
            "geographical.area",
            True,
        ),
    ]

    value_mapping = {
        "geographical_area_sid": "sid",
        "geographical_area_id": "area_id",
        "validity_start_date": "valid_between_lower",
        "validity_end_date": "valid_between_upper",
        "geographical_code": "area_code",
        "parent_geographical_area_group_sid": "parent__sid",
    }

    record_code = "250"
    subrecord_code = "00"

    xml_object_tag = "geographical.area"

    identity_fields = [
        "sid",
    ]

    sid: int = None
    area_id: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None
    area_code: int = None
    parent__sid: int = None


class NewGeographicalAreaDescriptionParser(Writable, BaseTaricParser):
    model = GeographicalAreaDescription

    model_links = [
        ModelLink(
            GeographicalArea,
            [
                ModelLinkField("described_geographicalarea__sid", "sid"),
                ModelLinkField("described_geographicalarea__area_id", "area_id"),
            ],
            "geographical.area",
        ),
    ]

    value_mapping = {
        "geographical_area_description_period_sid": "sid",
        "geographical_area_sid": "described_geographicalarea__sid",
        "geographical_area_id": "described_geographicalarea__area_id",
    }

    record_code = "250"
    subrecord_code = "10"

    xml_object_tag = "geographical.area.description"

    identity_fields = [
        "sid",
        "described_geographicalarea__sid",
        "described_geographicalarea__area_id",
    ]

    allow_update_without_children = True

    sid: int = None
    described_geographicalarea__sid: int = None
    described_geographicalarea__area_id: str = None
    description: str = None


class NewGeographicalAreaDescriptionPeriodParser(
    Writable,
    BaseTaricParser,
    ChildPeriod,
):
    model = GeographicalAreaDescription
    parent_parser = NewGeographicalAreaDescriptionParser

    model_links = [
        ModelLink(
            GeographicalArea,
            [
                ModelLinkField("described_geographicalarea__sid", "sid"),
                ModelLinkField("described_geographicalarea__area_id", "area_id"),
            ],
            "geographical.area",
        ),
        ModelLink(
            GeographicalAreaDescription,
            [
                ModelLinkField("sid", "sid"),
            ],
            "geographical.area.description",
        ),
    ]

    value_mapping = {
        "geographical_area_description_period_sid": "sid",
        "geographical_area_sid": "described_geographicalarea__sid",
        "geographical_area_id": "described_geographicalarea__area_id",
        "validity_start_date": "validity_start",
    }

    record_code = "250"
    subrecord_code = "05"

    xml_object_tag = "geographical.area.description.period"

    identity_fields = [
        "sid",
    ]

    deletes_allowed = False
    sid: int = None
    described_geographicalarea__sid: int = None
    described_geographicalarea__area_id: str = None
    validity_start: date = None


class NewGeographicalMembershipParser(ValidityMixin, Writable, BaseTaricParser):
    model = GeographicalMembership

    model_links = [
        ModelLink(
            GeographicalArea,
            [
                ModelLinkField("member__sid", "sid"),
            ],
            "geographical.area",
        ),
        ModelLink(
            GeographicalArea,
            [
                ModelLinkField("geo_group__sid", "sid"),
            ],
            "geographical.area",
        ),
    ]

    value_mapping = {
        "geographical_area_sid": "member__sid",
        "geographical_area_group_sid": "geo_group__sid",
        "validity_start_date": "valid_between_lower",
        "validity_end_date": "valid_between_upper",
    }

    record_code = "250"
    subrecord_code = "15"

    xml_object_tag = "geographical.membership"

    identity_fields = [
        "member__sid",
        "geo_group__sid",
    ]

    member__sid: int = None
    geo_group__sid: int = None
    valid_between_lower: date = None
    valid_between_upper: date = None
