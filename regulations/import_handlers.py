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

    def clean(self, data: dict) -> dict:
        data["information_text"], data["public_identifier"], data["url"] = data[
            "information_text"
        ]
        return super().clean(data)


class BaseRegulationThroughTableHandler(BaseHandler):
    links = ({"model": models.Regulation, "name": "target_regulation"},)
    serializer_class = serializers.RegulationImporterSerializer
    abstract = True


class AmendmentRegulationHandler(BaseRegulationThroughTableHandler):
    identifying_fields = ("role_type", "regulation_id")
    serializer_class = serializers.RegulationImporterSerializer
    xml_model = parsers.ModificationRegulationParser

    def clean(self, data: dict) -> dict:
        data["information_text"], data["public_identifier"], data["url"] = data[
            "information_text"
        ]
        return super().clean(data)

    @transaction.atomic
    def save(self, data: dict):
        target_regulation = data.pop("target_regulation")
        enacting_regulation = super().save(data)
        return serializers.AmendmentSerializer().create(
            {
                "target_regulation": target_regulation,
                "enacting_regulation": enacting_regulation,
                "update_type": data["update_type"],
                "transaction_id": data["transaction_id"],
            },
        )


class BaseSuspensionRegulationHandler(BaseRegulationThroughTableHandler):
    serializer_class = serializers.RegulationImporterSerializer
    abstract = True

    def clean(self, data: dict) -> dict:
        self.suspension_data = {}
        if "effective_end_date" in data:
            self.suspension_data["effective_end_date"] = data.pop("effective_end_date")
        if "information_text" in data:
            data["information_text"], data["public_identifier"], data["url"] = data[
                "information_text"
            ]
        return super().clean(data)

    @transaction.atomic
    def save(self, data: dict):
        target_regulation = data.pop("target_regulation")
        enacting_regulation = super().save(data)
        return serializers.SuspensionSerializer().create(
            {
                "target_regulation": target_regulation,
                "enacting_regulation": enacting_regulation,
                "update_type": data["update_type"],
                "transaction_id": data["transaction_id"],
                **self.suspension_data,
            },
        )


class SuspensionRegulationHandler(BaseSuspensionRegulationHandler):
    identifying_fields = ("role_type", "regulation_id")
    serializer_class = serializers.RegulationImporterSerializer
    xml_model = parsers.FullTemporaryStopRegulationParser


@SuspensionRegulationHandler.register_dependant
class SuspensionRegulationActionHandler(BaseSuspensionRegulationHandler):
    identifying_fields = ("role_type", "regulation_id")
    dependencies = [SuspensionRegulationHandler]
    serializer_class = serializers.RegulationImporterSerializer
    xml_model = parsers.FullTemporaryStopActionParser


class ReplacementHandler(BaseRegulationThroughTableHandler):
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
