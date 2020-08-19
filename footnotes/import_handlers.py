from footnotes import import_parsers as parsers
from footnotes import serializers
from importer.handlers import BaseHandler


class FootnoteTypeHandler(BaseHandler):
    serializer_class = serializers.FootnoteTypeSerializer
    tag = parsers.FootnoteTypeParser.tag.name


@FootnoteTypeHandler.register_dependant
class FootnoteTypeDescriptionHandler(BaseHandler):
    dependencies = [FootnoteTypeHandler]
    serializer_class = serializers.FootnoteTypeSerializer
    tag = parsers.FootnoteTypeDescriptionParser.tag.name
