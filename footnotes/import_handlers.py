from footnotes import import_parsers as parsers
from footnotes import models
from footnotes import serializers
from importer.handlers import BaseHandler
from importer.taric import RecordParser


@RecordParser.use_for_xml_serialization
class FootnoteTypeHandler(BaseHandler):
    serializer_class = serializers.FootnoteTypeSerializer
    xml_model = parsers.FootnoteTypeParser


@FootnoteTypeHandler.register_dependant
class FootnoteTypeDescriptionHandler(BaseHandler):
    dependencies = [FootnoteTypeHandler]
    serializer_class = serializers.FootnoteTypeSerializer
    xml_model = parsers.FootnoteTypeDescriptionParser


@RecordParser.use_for_xml_serialization
class FootnoteHandler(BaseHandler):
    identifying_fields = "footnote_id", "footnote_type__footnote_type_id"
    links = (
        {
            "model": models.FootnoteType,
            "name": "footnote_type",
        },
    )
    serializer_class = serializers.FootnoteSerializer
    xml_model = parsers.FootnoteParser


class BaseFootnoteDescriptionHandler(BaseHandler):
    links = (
        {
            "identifying_fields": ("footnote_id", "footnote_type__footnote_type_id"),
            "model": models.Footnote,
            "name": "described_footnote",
        },
    )
    serializer_class = serializers.FootnoteDescriptionSerializer
    abstract = True


@RecordParser.use_for_xml_serialization
class FootnoteDescriptionHandler(BaseFootnoteDescriptionHandler):
    serializer_class = serializers.FootnoteDescriptionSerializer
    xml_model = parsers.FootnoteDescriptionParser


@FootnoteDescriptionHandler.register_dependant
class FootnoteDescriptionPeriodHandler(BaseFootnoteDescriptionHandler):
    dependencies = [FootnoteDescriptionHandler]
    serializer_class = serializers.FootnoteDescriptionSerializer
    xml_model = parsers.FootnoteDescriptionPeriodParser
