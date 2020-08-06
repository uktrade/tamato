import logging

from commodities import serializers, models
from common.validators import UpdateType
from footnotes.models import Footnote, FootnoteType
from importer.handlers import ElementHandler
from importer.handlers import TextElement
from importer.handlers import ValidityMixin
from importer.handlers import Writable
from importer.namespaces import Tag
from importer.taric import Record


logger = logging.getLogger(__name__)


@Record.register_child("goods_nomenclature")
class GoodsNomenclature(ValidityMixin, Writable, ElementHandler):
    serializer_class = serializers.GoodsNomenclatureSerializer

    tag = Tag("goods.nomenclature")
    sid = TextElement(Tag("goods.nomenclature.sid"))
    item_id = TextElement(Tag("goods.nomenclature.item.id"))
    suffix = TextElement(Tag("producline.suffix"))  # XXX not a typo
    valid_between_lower = TextElement(Tag("validity.start.date"))
    valid_between_upper = TextElement(Tag("validity.end.date"))
    statistical = TextElement(Tag("statistical.indicator"))


@Record.register_child("goods_nomenclature_origin")
class GoodsNomenclatureOrigin(Writable, ElementHandler):
    tag = Tag("goods.nomenclature.origin")

    sid = TextElement(Tag("goods.nomenclature.sid"))
    derived_item_id = TextElement(Tag("derived.goods.nomenclature.item.id"))
    derived_suffix = TextElement(Tag("derived.productline.suffix"))
    item_id = TextElement(Tag("goods.nomenclature.item.id"))
    suffix = TextElement(Tag("productline.suffix"))


@Record.register_child("goods_nomenclature_description")
class GoodsNomenclatureDescription(Writable, ElementHandler):
    serializer_class = serializers.GoodsNomenclatureDescriptionSerializer

    tag = Tag("goods.nomenclature.description")
    goods_nomenclature_description_period_sid = TextElement(
        "goods.nomenclature.description.period.sid"
    )
    language_id = TextElement(Tag("language.id"))
    goods_nomenclature_sid = TextElement(Tag("goods.nomenclature.sid"))
    goods_nomenclature_item_id = TextElement(Tag("goods.nomenclature.item.id"))
    productline_suffix = TextElement(Tag("productline.suffix"))
    description = TextElement(Tag("description"))


@Record.register_child("goods_nomenclature_description_period")
class GoodsNomenclatureDescriptionPeriod(Writable, ElementHandler):
    tag = Tag("goods.nomenclature.description.period")
    goods_nomenclature_description_period_sid = TextElement(
        "goods.nomenclature.description.period.sid"
    )
    goods_nomenclature_sid = TextElement(Tag("goods.nomenclature.sid"))
    valid_between_lower = TextElement(Tag("validity.start.date"))
    goods_nomenclature_item_id = TextElement(Tag("goods.nomenclature.item.id"))
    productline_suffix = TextElement(Tag("productline.suffix"))


@Record.register_child("goods_nomenclature_indent")
class GoodsNomenclatureIndents(ValidityMixin, Writable, ElementHandler):
    serializer_class = serializers.GoodsNomenclatureIndentSerializer

    tag = Tag("goods.nomenclature.indents")
    sid = TextElement(Tag("goods.nomenclature.indent.sid"))
    goods_nomenclature_sid = TextElement(Tag("goods.nomenclature.sid"))
    valid_between_lower = TextElement(Tag("validity.start.date"))
    number_indents = TextElement(Tag("number.indents"))
    goods_nomenclature_item_id = TextElement(Tag("goods.nomenclature.item.id"))
    productline_suffix = TextElement(Tag("productline.suffix"))

    def clean(self):
        super().clean()
        good = models.GoodsNomenclature.objects.get_latest_version(
            sid=self.data.pop("goods_nomenclature_sid")
        )
        self.data["indented_goods_nomenclature"] = good


@Record.register_child("footnote_association_goods_nomenclature")
class FootnoteAssociationGoodsNomenclature(ValidityMixin, Writable, ElementHandler):
    serializer_class = serializers.FootnoteAssociationGoodsNomenclatureSerializer

    tag = Tag("footnote.association.goods.nomenclature")

    goods_nomenclature_sid = TextElement(Tag("goods.nomenclature.sid"))
    footnote_id = TextElement(Tag("footnote.id"))
    footnote_type_id = TextElement(Tag("footnote.type"))

    # valid_between_lower = TextElement(Tag("validity.start.date"))
    # valid_between_upper = TextElement(Tag("validity.end.date"))

    def create(self, data, workbasket_id):
        data["update_type"] = UpdateType.CREATE.value
        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Gather foreign keys
        good = models.GoodsNomenclature.objects.get_latest_version(
            sid=self.data.pop("goods_nomenclature_sid")
        )
        footnote_type = FootnoteType.objects.get_latest_version(
            footnote_type_id=self.data.pop("footnote_type_id")
        )
        footnote = Footnote.objects.get_latest_version(
            footnote_id=self.data.pop("footnote_id"), footnote_type=footnote_type,
        )

        data.update(
            workbasket_id=workbasket_id,
            associated_footnote=footnote,
            goods_nomenclature=good,
        )
        logger.debug(f"Creating {self.__class__.__name__}: {data}")
        serializer.create(data)
