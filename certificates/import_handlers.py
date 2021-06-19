from certificates import import_parsers as parsers
from certificates import models
from certificates import serializers
from importer.handlers import BaseHandler
from importer.taric import RecordParser


@RecordParser.use_for_xml_serialization
class CertificateTypeHandler(BaseHandler):
    serializer_class = serializers.CertificateTypeSerializer
    xml_model = parsers.CertificateTypeParser


@CertificateTypeHandler.register_dependant
class CertificateTypeDescriptionHandler(BaseHandler):
    dependencies = [
        CertificateTypeHandler,
    ]
    serializer_class = serializers.CertificateTypeSerializer
    xml_model = parsers.CertificateTypeDescriptionParser


@RecordParser.use_for_xml_serialization
class CertificateHandler(BaseHandler):
    identifying_fields = "sid", "certificate_type__sid"
    links = (
        {
            "model": models.CertificateType,
            "name": "certificate_type",
        },
    )

    serializer_class = serializers.CertificateSerializer
    xml_model = parsers.CertificateParser


class BaseCertificateDescriptionHandler(BaseHandler):
    links = (
        {
            "identifying_fields": ("sid", "certificate_type__sid"),
            "model": models.Certificate,
            "name": "described_certificate",
        },
    )
    serializer_class = serializers.CertificateDescriptionSerializer
    abstract = True


@RecordParser.use_for_xml_serialization
class CertificateDescriptionHandler(BaseCertificateDescriptionHandler):
    serializer_class = serializers.CertificateDescriptionSerializer
    xml_model = parsers.CertificateDescriptionParser


@CertificateDescriptionHandler.register_dependant
class CertificateDescriptionPeriodHandler(BaseCertificateDescriptionHandler):
    dependencies = [
        CertificateDescriptionHandler,
    ]
    serializer_class = serializers.CertificateDescriptionSerializer
    xml_model = parsers.CertificateDescriptionPeriodParser
