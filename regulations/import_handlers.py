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
    serializer_class = serializers.RegulationImporterSerializer
    tag = parsers.BaseRegulationParser.tag.name


class BaseRegulationThroughTableHandler(BaseHandler):
    links = ({"model": models.Regulation, "name": "target_regulation"},)
    serializer_class = serializers.RegulationImporterSerializer
    tag = "BaseRegulationThroughTableHandler"


class AmendmentRegulationHandler(BaseRegulationThroughTableHandler):
    serializer_class = serializers.RegulationImporterSerializer
    tag = parsers.ModificationRegulationParser.tag.name

    @transaction.atomic
    def save(self, data: dict):
        target_regulation = data.pop("target_regulation")
        enacting_regulation = super().save(data)
        return serializers.AmendmentSerializer().create(
            {
                "target_regulation": target_regulation,
                "enacting_regulation": enacting_regulation,
                "update_type": data["update_type"],
                "workbasket_id": data["workbasket_id"],
            }
        )


class BaseSuspensionRegulationHandler(BaseRegulationThroughTableHandler):
    serializer_class = serializers.RegulationImporterSerializer
    tag = "BaseSuspensionRegulationHandler"

    def clean(self, data: dict) -> dict:
        self.suspension_data = {"effective_end_date": data.pop("effective_end_date")}
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
                "workbasket_id": data["workbasket_id"],
                **self.suspension_data,
            }
        )


class SuspensionRegulationHandler(BaseSuspensionRegulationHandler):
    identifying_fields = ("role_type", "regulation_id")
    serializer_class = serializers.RegulationImporterSerializer
    tag = parsers.FullTemporaryStopRegulationParser.tag.name


@SuspensionRegulationHandler.register_dependant
class SuspensionRegulationActionHandler(BaseSuspensionRegulationHandler):
    identifying_fields = ("role_type", "regulation_id")
    dependencies = [SuspensionRegulationHandler]
    serializer_class = serializers.RegulationImporterSerializer
    tag = parsers.FullTemporaryStopActionParser.tag.name


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
    tag = parsers.RegulationReplacementParser.tag.name
