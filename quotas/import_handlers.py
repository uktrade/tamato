from importer.handlers import BaseHandler
from quotas import import_parsers as parsers
from quotas import serializers


class QuotaOrderNumberHandler(BaseHandler):
    serializer_class = serializers.QuotaOrderNumberSerializer
    tag = parsers.QuotaOrderNumberParser.tag.name
