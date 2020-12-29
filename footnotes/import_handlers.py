from footnotes import import_parsers as parsers
from footnotes import models
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


class FootnoteHandler(BaseHandler):
    identifying_fields = "footnote_id", "footnote_type__footnote_type_id"
    links = (
        {
            "model": models.FootnoteType,
            "name": "footnote_type",
        },
    )
    serializer_class = serializers.FootnoteSerializer
    tag = parsers.FootnoteParser.tag.name


class BaseFootnoteDescriptionHandler(BaseHandler):
    links = (
        {
            "identifying_fields": ("footnote_id", "footnote_type__footnote_type_id"),
            "model": models.Footnote,
            "name": "described_footnote",
        },
    )
    serializer_class = serializers.FootnoteDescriptionSerializer
    tag = "BaseFootnoteDescriptionHandler"


class FootnoteDescriptionHandler(BaseFootnoteDescriptionHandler):
    serializer_class = serializers.FootnoteDescriptionSerializer
    tag = parsers.FootnoteDescriptionParser.tag.name


@FootnoteDescriptionHandler.register_dependant
class FootnoteDescriptionPeriodHandler(BaseFootnoteDescriptionHandler):
    dependencies = [FootnoteDescriptionHandler]
    serializer_class = serializers.FootnoteDescriptionSerializer
    tag = parsers.FootnoteDescriptionPeriodParser.tag.name
