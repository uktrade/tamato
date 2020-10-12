import logging

from commodities import import_parsers as parsers
from commodities import models
from commodities import serializers
from footnotes.models import Footnote
from footnotes.models import FootnoteType
from importer.handlers import BaseHandler


logger = logging.getLogger(__name__)


class InvalidIndentError(Exception):
    pass


class GoodsNomenclatureHandler(BaseHandler):
    serializer_class = serializers.GoodsNomenclatureSerializer
    tag = parsers.GoodsNomenclatureParser.tag.name


class GoodsNomenclatureOriginHandler(BaseHandler):
    serializer_class = serializers.GoodsNomenclatureSerializer
    tag = parsers.GoodsNomenclatureOriginParser.tag.name


class BaseGoodsNomenclatureDescriptionHandler(BaseHandler):
    links = (
        {
            "identifying_fields": ("sid", "item_id"),
            "model": models.GoodsNomenclature,
            "name": "described_goods_nomenclature",
        },
    )
    serializer_class = serializers.GoodsNomenclatureDescriptionSerializer
    tag = "BaseGoodsNomenclatureDescriptionHandler"


class GoodsNomenclatureDescriptionHandler(BaseGoodsNomenclatureDescriptionHandler):
    serializer_class = serializers.GoodsNomenclatureDescriptionSerializer
    tag = parsers.GoodsNomenclatureDescriptionParser.tag.name


@GoodsNomenclatureDescriptionHandler.register_dependant
class GoodsNomenclatureDescriptionPeriodHandler(
    BaseGoodsNomenclatureDescriptionHandler
):
    dependencies = [GoodsNomenclatureDescriptionHandler]
    serializer_class = serializers.GoodsNomenclatureDescriptionSerializer
    tag = parsers.GoodsNomenclatureDescriptionPeriodParser.tag.name


class GoodsNomenclatureIndentHandler(BaseHandler):
    links = (
        {"model": models.GoodsNomenclature, "name": "indented_goods_nomenclature"},
    )
    serializer_class = serializers.GoodsNomenclatureIndentSerializer
    tag = parsers.GoodsNomenclatureIndentsParser.tag.name

    def __init__(self, *args, **kwargs):
        super(GoodsNomenclatureIndentHandler, self).__init__(*args, **kwargs)
        self.extra_data = {}

    def clean(self, data: dict) -> dict:
        self.extra_data["indent"] = int(data["indent"])
        return super(GoodsNomenclatureIndentHandler, self).clean(data)

    def save(self, data: dict):
        indent = self.extra_data.pop("indent")
        data.update(**self.extra_data)

        item_id = data["indented_goods_nomenclature"].item_id

        if (
            indent == 0 and item_id[2:] == "00000000"
        ):  # This is a root indent (i.e. a chapter heading)
            return models.GoodsNomenclatureIndent.add_root(**data)

        chapter_heading = item_id[:2]

        parent_indent = indent + 1

        # TODO: Parents may change over an indents lifetime, need to check for all parents over the lifetime of
        # an indent and create a series of updates to match them all.
        # Updates aren't setup yet, do once they are.
        parent = max(
            models.GoodsNomenclatureIndent.objects.filter(
                indented_goods_nomenclature__item_id__startswith=chapter_heading,
                indented_goods_nomenclature__item_id__lte=item_id,
                depth=parent_indent,
                valid_between__contains=data["valid_between"],
            ).current(),
            key=lambda x: x.indented_goods_nomenclature.item_id,
        )

        return parent.add_child(**data)

    def post_save(self, obj):
        """
        There is a possible (albeit unlikely) scenario when introducing an indent that the
        new indent is put between an existing indent and it's children (i.e. it becomes the
        new parent for those children).

        As the old system had no real materialized tree behind the system it is not
        unreasonable to suggest this as a possibility.

        This method handles this by checking for any children which need to be moved
        in case this happens.
        """

        # TODO: Implement this scenario (requires updating to be implemented first).

        return super(GoodsNomenclatureIndentHandler, self).post_save(obj)


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
