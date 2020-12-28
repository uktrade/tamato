from datetime import datetime

from geo_areas.models import GeographicalArea
from importer.handlers import BaseHandler
from measures.models import MeasurementUnit
from measures.models import MeasurementUnitQualifier
from measures.models import MonetaryUnit
from quotas import import_parsers as parsers
from quotas import models
from quotas import serializers


class QuotaOrderNumberHandler(BaseHandler):
    serializer_class = serializers.QuotaOrderNumberSerializer
    tag = parsers.QuotaOrderNumberParser.tag.name


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
    tag = parsers.QuotaOrderNumberOriginParser.tag.name


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
    tag = parsers.QuotaOrderNumberOriginExclusionParser.tag.name


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
    tag = parsers.QuotaDefinitionParser.tag.name


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
    tag = parsers.QuotaAssociationParser.tag.name


class QuotaSuspensionHandler(BaseHandler):
    links = (
        {
            "model": models.QuotaDefinition,
            "name": "quota_definition",
        },
    )
    serializer_class = serializers.QuotaSuspensionSerializer
    tag = parsers.QuotaSuspensionPeriodParser.tag.name


class QuotaBlockingHandler(BaseHandler):
    links = (
        {
            "model": models.QuotaDefinition,
            "name": "quota_definition",
        },
    )
    serializer_class = serializers.QuotaBlockingSerializer
    tag = parsers.QuotaBlockingPeriodParser.tag.name


class QuotaEventHandler(BaseHandler):
    identifying_fields = ("subrecord_code", "quota_definition__sid")
    links = ({"model": models.QuotaDefinition, "name": "quota_definition"},)
    serializer_class = serializers.QuotaEventImporterSerializer
    tag = parsers.QuotaEventParser.tag.name

    def clean(self, data: dict) -> dict:
        data["occurrence_timestamp"] = datetime.fromisoformat(
            data["occurrence_timestamp"]
        )
        return super().clean(data)

    def pre_save(self, data: dict, links: dict) -> dict:
        data = super().pre_save(data, links)
        data.get("data", {}).pop("quota_definition__sid")
        return data
