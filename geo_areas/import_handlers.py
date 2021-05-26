from geo_areas import import_parsers as parsers
from geo_areas import models
from geo_areas import serializers
from importer.handlers import BaseHandler


class GeographicalAreaHandler(BaseHandler):
    links = (
        {
            "model": models.GeographicalArea,
            "name": "parent",
            "optional": True,
        },
    )
    serializer_class = serializers.GeographicalAreaImporterSerializer
    tag = parsers.GeographicalAreaParser.tag.name


class BaseGeographicalAreaDescriptionHandler(BaseHandler):
    links = (
        {
            "model": models.GeographicalArea,
            "name": "area",
        },
    )
    serializer_class = serializers.GeographicalAreaDescriptionSerializer
    tag = "BaseGeographicalAreaDescriptionHandler"


class GeographicalAreaDescriptionHandler(BaseGeographicalAreaDescriptionHandler):
    serializer_class = serializers.GeographicalAreaDescriptionImporterSerializer
    tag = parsers.GeographicalAreaDescriptionParser.tag.name


@GeographicalAreaDescriptionHandler.register_dependant
class GeographicalAreaDescriptionPeriodHandler(BaseGeographicalAreaDescriptionHandler):
    dependencies = [GeographicalAreaDescriptionHandler]
    serializer_class = serializers.GeographicalAreaDescriptionImporterSerializer
    tag = parsers.GeographicalAreaDescriptionPeriodParser.tag.name


class GeographicalMembershipHandler(BaseHandler):
    identifying_fields = ("geo_group__sid", "member__sid")
    links = (
        {
            "model": models.GeographicalArea,
            "name": "geo_group",
        },
        {
            "model": models.GeographicalArea,
            "name": "member",
        },
    )
    serializer_class = serializers.GeographicalMembershipSerializer
    tag = parsers.GeographicalMembershipParser.tag.name
