from django.db import transaction

from importer.handlers import BaseHandler
from regulations import import_parsers as parsers
from regulations import models
from regulations import serializers


class RegulationGroupHandler(BaseHandler):
    serializer_class = serializers.GroupSerializer
    tag = parsers.RegulationGroupParser.tag.name


@RegulationGroupHandler.register_dependant
class RegulationGroupDescriptionHandler(BaseHandler):
    dependencies = [RegulationGroupHandler]
    serializer_class = serializers.GroupSerializer
    tag = parsers.RegulationGroupDescriptionParser.tag.name


class RegulationHandler(BaseHandler):
    links = (
        {
            "model": models.Group,
            "name": "regulation_group",
            "optional": True,
        },
    )
    serializer_class = serializers.BaseRegulationSerializer
    tag = parsers.BaseRegulationParser.tag.name


class BaseRegulationThroughTableHandler(BaseHandler):
    identifying_fields = (
        "enacting_regulation__role_type",
        "enacting_regulation__regulation_id",
    )
    links = ({"model": models.Regulation, "name": "target_regulation"},)
    serializer_class = serializers.BaseRegulationSerializer
    tag = "BaseRegulationThroughTableHandler"

    def clean(self, data: dict) -> dict:
        enacting_regulation_data = {}
        for key in data.keys():
            if key.startswith("enacting_regulation__"):
                enacting_regulation_data[key.split("__")[1]] = data[key]

        data["enacting_regulation"] = enacting_regulation_data
        data["enacting_regulation"]["update_type"] = data["update_type"]
        return super().clean(data)

    @transaction.atomic
    def save(self, data: dict):
        enacting_regulation = serializers.BaseRegulationSerializer().create(
            {
                "update_type": data["update_type"],
                "transaction_id": data["transaction_id"],
                **data.pop("enacting_regulation"),
            },
        )
        data["enacting_regulation"] = enacting_regulation
        return super().save(data)


class AmendmentRegulationHandler(BaseRegulationThroughTableHandler):
    serializer_class = serializers.AmendmentSerializer
    tag = parsers.ModificationRegulationParser.tag.name


class SuspensionRegulationHandler(BaseRegulationThroughTableHandler):
    serializer_class = serializers.SuspensionSerializer
    tag = parsers.FullTemporaryStopRegulationParser.tag.name


@SuspensionRegulationHandler.register_dependant
class SuspensionRegulationActionHandler(BaseRegulationThroughTableHandler):
    dependencies = [SuspensionRegulationHandler]
    serializer_class = serializers.SuspensionSerializer
    tag = parsers.FullTemporaryStopActionParser.tag.name


class ReplacementHandler(BaseHandler):
    identifying_fields = (
        "enacting_regulation__regulation_id",
        "target_regulation__regulation_id",
    )
    links = (
        {
            "model": models.Regulation,
            "name": "target_regulation",
        },
        {
            "model": models.Regulation,
            "name": "enacting_regulation",
        },
    )
    serializer_class = serializers.ReplacementSerializer
    tag = parsers.RegulationReplacementParser.tag.name
