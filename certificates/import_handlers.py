from certificates import import_parsers as parsers
from certificates import serializers
from importer.handlers import BaseHandler


class CertificateTypeHandler(BaseHandler):
    serializer_class = serializers.CertificateTypeSerializer
    tag = parsers.CertificateTypeParser.tag.name


class CertificateTypeDescriptionHandler(BaseHandler):
    serializer_class = serializers.CertificateTypeSerializer
    tag = parsers.CertificateTypeDescriptionParser.tag.name


class CertificateHandler(BaseHandler):
    serializer_class = serializers.CertificateSerializer
    tag = parsers.CertificateParser.tag.name


class CertificateDescriptionHandler(BaseHandler):
    serializer_class = serializers.CertificateDescriptionSerializer
    tag = parsers.CertificateDescriptionParser.tag.name


class CertificateDescriptionPeriodHandler(BaseHandler):
    serializer_class = serializers.CertificateDescriptionSerializer
    tag = parsers.CertificateDescriptionPeriodParser.tag.name
