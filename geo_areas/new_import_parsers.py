from datetime import date

from geo_areas.import_handlers import *
from importer.new_parsers import ModelLink
from importer.new_parsers import ModelLinkField
from importer.new_parsers import NewElementParser
from importer.parsers import NewChildPeriod
from importer.parsers import NewValidityMixin
from importer.parsers import NewWritable


class NewGeographicalAreaParser(NewValidityMixin, NewWritable, NewElementParser):
    model = models.GeographicalArea

    model_links = [
        ModelLink(
            models.GeographicalArea,
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

    sid: int = None
    area_id: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None
    area_code: int = None
    parent__sid: int = None


class NewGeographicalAreaDescriptionParser(NewWritable, NewElementParser):
    model = models.GeographicalAreaDescription

    model_links = [
        ModelLink(
            models.GeographicalArea,
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

    sid: int = None
    described_geographicalarea__sid: int = None
    described_geographicalarea__area_id: str = None
    description: str = None


class NewGeographicalAreaDescriptionPeriodParser(
    NewWritable,
    NewElementParser,
    NewChildPeriod,
):
    model = models.GeographicalAreaDescription
    parent_parser = NewGeographicalAreaDescriptionParser

    model_links = [
        ModelLink(
            models.GeographicalArea,
            [
                ModelLinkField("described_geographicalarea__sid", "sid"),
                ModelLinkField("described_geographicalarea__area_id", "area_id"),
            ],
            "geographical.area",
        ),
        ModelLink(
            models.GeographicalAreaDescription,
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

    sid: int = None
    described_geographicalarea__sid: int = None
    described_geographicalarea__area_id: str = None
    validity_start: date = None


class NewGeographicalMembershipParser(NewValidityMixin, NewWritable, NewElementParser):
    model = models.GeographicalMembership

    model_links = [
        ModelLink(
            models.GeographicalArea,
            [
                ModelLinkField("member__sid", "sid"),
            ],
            "geographical.area",
        ),
        ModelLink(
            models.GeographicalArea,
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

    member__sid: int = None
    geo_group__sid: int = None
    valid_between_lower: date = None
    valid_between_upper: date = None
