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
    xml_model = parsers.GeographicalAreaParser


class BaseGeographicalAreaDescriptionHandler(BaseHandler):
    links = (
        {
            "model": models.GeographicalArea,
            "name": "described_geographicalarea",
        },
    )
    serializer_class = serializers.GeographicalAreaDescriptionSerializer
    abstract = True


class GeographicalAreaDescriptionHandler(BaseGeographicalAreaDescriptionHandler):
    serializer_class = serializers.GeographicalAreaDescriptionImporterSerializer
    xml_model = parsers.GeographicalAreaDescriptionParser


@GeographicalAreaDescriptionHandler.register_dependant
class GeographicalAreaDescriptionPeriodHandler(BaseGeographicalAreaDescriptionHandler):
    dependencies = [GeographicalAreaDescriptionHandler]
    serializer_class = serializers.GeographicalAreaDescriptionImporterSerializer
    xml_model = parsers.GeographicalAreaDescriptionPeriodParser


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
    xml_model = parsers.GeographicalMembershipParser
