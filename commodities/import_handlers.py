import logging

from commodities import import_parsers as parsers
from commodities import models
from commodities import serializers
from footnotes.models import Footnote
from footnotes.models import FootnoteType
from importer.handlers import BaseHandler


logger = logging.getLogger(__name__)


class GoodsNomenclatureHandler(BaseHandler):
    serializer_class = serializers.GoodsNomenclatureSerializer
    tag = parsers.GoodsNomenclatureParser.tag.name


class GoodsNomenclatureOriginHandler(BaseHandler):
    serializer_class = serializers.GoodsNomenclatureSerializer
    tag = parsers.GoodsNomenclatureOriginParser.tag.name


class GoodsNomenclatureDescriptionHandler(BaseHandler):
    serializer_class = serializers.GoodsNomenclatureDescriptionSerializer
    tag = parsers.GoodsNomenclatureDescriptionParser.tag.name


class GoodsNomenclatureDescriptionPeriodHandler(BaseHandler):
    serializer_class = serializers.GoodsNomenclatureDescriptionSerializer
    tag = parsers.GoodsNomenclatureDescriptionPeriodParser.tag.name


class GoodsNomenclatureIndentsHandler(BaseHandler):
    serializer_class = serializers.GoodsNomenclatureIndentSerializer
    tag = parsers.GoodsNomenclatureIndentsParser.tag.name


class FootnoteAssociationGoodsNomenclatureHandler(BaseHandler):
    identifying_fields = (
        "goods_nomenclature__sid",
        "associated_footnote__footnote_id",
        "associated_footnote__footnote_type_id",
    )

    links = (
        {
            "model": models.GoodsNomenclature,
            "name": "goods_nomenclature",
            "optional": False,
        },
        {
            "model": Footnote,
            "name": "associated_footnote",
            "optional": False,
            "identifying_fields": ("footnote_id", "footnote_type_id"),
        },
    )
    serializer_class = serializers.FootnoteAssociationGoodsNomenclatureSerializer
    tag = parsers.FootnoteAssociationGoodsNomenclatureParser.tag.name

    def get_associated_footnote_link(self, model, kwargs):
        kwargs["footnote_type"] = FootnoteType.objects.get_latest_version(
            footnote_type_id=kwargs.pop("footnote_type_id")
        )
        return model.objects.get_latest_version(**kwargs)
