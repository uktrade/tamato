from datetime import datetime

from geo_areas.models import GeographicalArea
from importer.handlers import BaseHandler
from importer.taric import RecordParser
from measures.models import MeasurementUnit
from measures.models import MeasurementUnitQualifier
from measures.models import MonetaryUnit
from quotas import import_parsers as parsers
from quotas import models
from quotas import serializers


@RecordParser.use_for_xml_serialization
class QuotaOrderNumberHandler(BaseHandler):
    serializer_class = serializers.QuotaOrderNumberSerializer
    xml_model = parsers.QuotaOrderNumberParser


@RecordParser.use_for_xml_serialization
class QuotaOrderNumberOriginHandler(BaseHandler):
    links = (
        {
            "model": models.QuotaOrderNumber,
            "name": "order_number",
        },
        {
            "model": GeographicalArea,
            "name": "geographical_area",
        },
    )
    serializer_class = serializers.QuotaOrderNumberOriginSerializer
    xml_model = parsers.QuotaOrderNumberOriginParser


@RecordParser.use_for_xml_serialization
class QuotaOrderNumberOriginExclusionHandler(BaseHandler):
    identifying_fields = ("origin__sid", "excluded_geographical_area__sid")
    links = (
        {
            "model": models.QuotaOrderNumberOrigin,
            "name": "origin",
        },
        {
            "model": GeographicalArea,
            "name": "excluded_geographical_area",
        },
    )

    serializer_class = serializers.QuotaOrderNumberOriginExclusionSerializer
    xml_model = parsers.QuotaOrderNumberOriginExclusionParser


@RecordParser.use_for_xml_serialization
class QuotaDefinitionHandler(BaseHandler):
    links = (
        {"model": models.QuotaOrderNumber, "name": "order_number"},
        {"model": MonetaryUnit, "name": "monetary_unit", "optional": True},
        {"model": MeasurementUnit, "name": "measurement_unit", "optional": True},
        {
            "model": MeasurementUnitQualifier,
            "name": "measurement_unit_qualifier",
            "optional": True,
        },
    )
    serializer_class = serializers.QuotaDefinitionImporterSerializer
    xml_model = parsers.QuotaDefinitionParser


@RecordParser.use_for_xml_serialization
class QuotaAssociationHandler(BaseHandler):
    identifying_fields = "main_quota__sid", "sub_quota__sid"
    links = (
        {
            "model": models.QuotaDefinition,
            "name": "main_quota",
        },
        {"model": models.QuotaDefinition, "name": "sub_quota"},
    )
    serializer_class = serializers.QuotaAssociationSerializer
    xml_model = parsers.QuotaAssociationParser


@RecordParser.use_for_xml_serialization
class QuotaSuspensionHandler(BaseHandler):
    links = (
        {
            "model": models.QuotaDefinition,
            "name": "quota_definition",
        },
    )
    serializer_class = serializers.QuotaSuspensionSerializer
    xml_model = parsers.QuotaSuspensionParser


@RecordParser.use_for_xml_serialization
class QuotaBlockingHandler(BaseHandler):
    links = (
        {
            "model": models.QuotaDefinition,
            "name": "quota_definition",
        },
    )
    serializer_class = serializers.QuotaBlockingSerializer
    xml_model = parsers.QuotaBlockingParser


class QuotaEventHandler(BaseHandler):
    identifying_fields = ("subrecord_code", "quota_definition__sid")
    links = ({"model": models.QuotaDefinition, "name": "quota_definition"},)
    serializer_class = serializers.QuotaEventImporterSerializer
    xml_model = parsers.QuotaEventParser

    def clean(self, data: dict) -> dict:
        data["occurrence_timestamp"] = datetime.fromisoformat(
            data["occurrence_timestamp"],
        )
        return super().clean(data)

    def pre_save(self, data: dict, links: dict) -> dict:
        data = super().pre_save(data, links)
        data.get("data", {}).pop("quota_definition__sid")
        return data
