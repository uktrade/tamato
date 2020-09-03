from certificates import import_parsers as parsers
from certificates import models
from certificates import serializers
from importer.handlers import BaseHandler


class CertificateTypeHandler(BaseHandler):
    serializer_class = serializers.CertificateTypeSerializer
    tag = parsers.CertificateTypeParser.tag.name


@CertificateTypeHandler.register_dependant
class CertificateTypeDescriptionHandler(BaseHandler):
    dependencies = [
        CertificateTypeHandler,
    ]
    serializer_class = serializers.CertificateTypeSerializer
    tag = parsers.CertificateTypeDescriptionParser.tag.name


class CertificateHandler(BaseHandler):
    links = (
        {
            "model": models.CertificateType,
            "name": "certificate_type",
        },
    )

    serializer_class = serializers.CertificateSerializer
    tag = parsers.CertificateParser.tag.name


class BaseCertificateDescriptionHandler(BaseHandler):
    links = (
        {
            "identifying_fields": ("sid", "certificate_type__sid"),
            "model": models.Certificate,
            "name": "described_certificate",
        },
    )
    serializer_class = serializers.CertificateDescriptionSerializer
    tag = "BaseCertificateDescriptionHandler"

    def get_described_certificate_link(self, model, kwargs):
        certificate_type = models.CertificateType.objects.get_latest_version(
            sid=kwargs.pop("certificate_type__sid")
        )
        obj = model.objects.get_latest_version(
            certificate_type=certificate_type, **kwargs
        )
        return obj


class CertificateDescriptionHandler(BaseCertificateDescriptionHandler):
    serializer_class = serializers.CertificateDescriptionSerializer
    tag = parsers.CertificateDescriptionParser.tag.name


@CertificateDescriptionHandler.register_dependant
class CertificateDescriptionPeriodHandler(BaseCertificateDescriptionHandler):
    dependencies = [
        CertificateDescriptionHandler,
    ]
    serializer_class = serializers.CertificateDescriptionSerializer
    tag = parsers.CertificateDescriptionPeriodParser.tag.name
