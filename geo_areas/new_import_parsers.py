from datetime import date

from geo_areas.import_handlers import *
from importer.new_parsers import NewElementParser
from importer.parsers import NewValidityMixin
from importer.parsers import NewWritable


class NewGeographicalAreaParser(NewValidityMixin, NewWritable, NewElementParser):
    handler = GeographicalAreaHandler

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
    handler = GeographicalAreaDescriptionHandler

    record_code = "250"
    subrecord_code = "10"

    xml_object_tag = "geographical.area.description"

    sid: str = None
    language_id: str = None
    described_geographicalarea__sid: str = None
    described_geographicalarea__area_id: str = None
    description: str = None


class NewGeographicalAreaDescriptionPeriodParser(NewWritable, NewElementParser):
    handler = GeographicalAreaDescriptionPeriodHandler

    record_code = "250"
    subrecord_code = "05"

    xml_object_tag = "geographical.area.description.period"

    sid: str = None
    described_geographicalarea__sid: str = None
    validity_start: str = None
    described_geographicalarea__area_id: str = None


class NewGeographicalMembershipParser(NewValidityMixin, NewWritable, NewElementParser):
    handler = GeographicalMembershipHandler

    record_code = "250"
    subrecord_code = "15"

    xml_object_tag = "geographical.area.membership"

    member__sid: str = None
    geo_group__sid: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None
