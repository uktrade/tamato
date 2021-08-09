from django.db import transaction

from importer.handlers import BaseHandler
from importer.taric import RecordParser
from regulations import import_parsers as parsers
from regulations import models
from regulations import serializers


@RecordParser.use_for_xml_serialization
class RegulationGroupHandler(BaseHandler):
    serializer_class = serializers.GroupSerializer
    xml_model = parsers.RegulationGroupParser


@RegulationGroupHandler.register_dependant
class RegulationGroupDescriptionHandler(BaseHandler):
    dependencies = [RegulationGroupHandler]
    serializer_class = serializers.GroupSerializer
    xml_model = parsers.RegulationGroupDescriptionParser


@RecordParser.use_for_xml_serialization  # FIXME
class RegulationHandler(BaseHandler):
    links = (
        {
            "model": models.Group,
            "name": "regulation_group",
            "optional": True,
        },
    )
    serializer_class = serializers.RegulationImporterSerializer
    xml_model = parsers.BaseRegulationParser



class BaseRegulationThroughTableHandler(BaseHandler):
    identifying_fields = (
        "enacting_regulation__role_type",
        "enacting_regulation__regulation_id",
    )
    links = ({"model": models.Regulation, "name": "target_regulation"},)
    serializer_class = serializers.RegulationImporterSerializer
    abstract = True

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
        enacting_regulation = serializers.RegulationImporterSerializer().create(
            {
                "update_type": data["update_type"],
                "transaction_id": data["transaction_id"],
                **data.pop("enacting_regulation"),
            },
        )
        data["enacting_regulation"] = enacting_regulation
        return super().save(data)


class AmendmentRegulationHandler(BaseRegulationThroughTableHandler):
    serializer_class = serializers.AmendmentImporterSerializer
    xml_model = parsers.ModificationRegulationParser


class SuspensionRegulationHandler(BaseRegulationThroughTableHandler):
    serializer_class = serializers.SuspensionImporterSerializer
    xml_model = parsers.FullTemporaryStopRegulationParser


@SuspensionRegulationHandler.register_dependant
class SuspensionRegulationActionHandler(BaseRegulationThroughTableHandler):
    dependencies = [SuspensionRegulationHandler]
    serializer_class = serializers.SuspensionImporterSerializer
    xml_model = parsers.FullTemporaryStopActionParser


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
    serializer_class = serializers.ReplacementImporterSerializer
    xml_model = parsers.RegulationReplacementParser
