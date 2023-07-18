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
        ),
    ]

    record_code = "250"
    subrecord_code = "00"

    xml_object_tag = "geographical.area"

    sid: str = None
    area_id: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None
    area_code: str = None
    parent__sid: str = None


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

    record_code = "250"
    subrecord_code = "10"

    xml_object_tag = "geographical.area.description"

    sid: str = None
    described_geographicalarea__sid: str = None
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
                ModelLinkField("geographical_area_description_period__sid", "sid"),
            ],
            "geographical.area.description",
        ),
    ]

    value_mapping = {
        "geographical_area_description_period__sid": "sid",
    }

    record_code = "250"
    subrecord_code = "05"

    xml_object_tag = "geographical.area.description.period"

    sid: str = None
    described_geographicalarea__sid: str = None
    described_geographicalarea__area_id: str = None
    validity_start: str = None


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

    record_code = "250"
    subrecord_code = "15"

    xml_object_tag = "geographical.area.membership"

    member__sid: str = None
    geo_group__sid: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None
