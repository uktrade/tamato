from additional_codes import import_parsers as parsers
from additional_codes import models
from additional_codes import serializers
from importer.handlers import BaseHandler


class AdditionalCodeTypeHandler(BaseHandler):
    serializer_class = serializers.AdditionalCodeTypeSerializer
    tag = parsers.AdditionalCodeTypeParser.tag.name


@AdditionalCodeTypeHandler.register_dependant
class AdditionalCodeTypeDescriptionHandler(BaseHandler):
    dependencies = [AdditionalCodeTypeHandler]
    serializer_class = serializers.AdditionalCodeTypeSerializer
    tag = parsers.AdditionalCodeTypeDescriptionParser.tag.name


class AdditionalCodeHandler(BaseHandler):
    links = (
        {
            "model": models.AdditionalCodeType,
            "name": "type",
        },
    )
    serializer_class = serializers.AdditionalCodeImporterSerializer
    tag = parsers.AdditionalCodeParser.tag.name


class BaseAdditionalCodeDescriptionHandler(BaseHandler):
    links = (
        {
            "identifying_fields": ("sid", "code", "type__sid"),
            "model": models.AdditionalCode,
            "name": "described_additionalcode",
        },
    )
    serializer_class = serializers.AdditionalCodeDescriptionImporterSerializer
    tag = "BaseAdditionalCodeDescriptionHandler"

    def get_described_additionalcode_link(self, model, kwargs):
        code_type = models.AdditionalCodeType.objects.get_latest_version(
            sid=kwargs.pop("type__sid"),
        )
        obj = model.objects.get_latest_version(type=code_type, **kwargs)
        return obj


class AdditionalCodeDescriptionHandler(BaseAdditionalCodeDescriptionHandler):
    serializer_class = serializers.AdditionalCodeDescriptionImporterSerializer
    tag = parsers.AdditionalCodeDescriptionParser.tag.name


@AdditionalCodeDescriptionHandler.register_dependant
class AdditionalCodeDescriptionPeriodHandler(BaseAdditionalCodeDescriptionHandler):
    dependencies = [AdditionalCodeDescriptionHandler]
    serializer_class = serializers.AdditionalCodeDescriptionImporterSerializer
    tag = parsers.AdditionalCodeDescriptionPeriodParser.tag.name
