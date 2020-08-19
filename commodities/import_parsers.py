import logging

from commodities import models
from importer.namespaces import Tag
from importer.parsers import ElementParser
from importer.parsers import TextElement
from importer.parsers import ValidityMixin
from importer.parsers import Writable
from importer.taric import Record


logger = logging.getLogger(__name__)


@Record.register_child("goods_nomenclature")
class GoodsNomenclatureParser(ValidityMixin, Writable, ElementParser):
    tag = Tag("goods.nomenclature")

    sid = TextElement(Tag("goods.nomenclature.sid"))
    item_id = TextElement(Tag("goods.nomenclature.item.id"))
    suffix = TextElement(Tag("producline.suffix"))  # XXX not a typo
    valid_between_lower = TextElement(Tag("validity.start.date"))
    valid_between_upper = TextElement(Tag("validity.end.date"))
    statistical = TextElement(Tag("statistical.indicator"))


@Record.register_child("goods_nomenclature_origin")
class GoodsNomenclatureOriginParser(Writable, ElementParser):
    tag = Tag("goods.nomenclature.origin")

    sid = TextElement(Tag("goods.nomenclature.sid"))
    derived_item_id = TextElement(Tag("derived.goods.nomenclature.item.id"))
    derived_suffix = TextElement(Tag("derived.productline.suffix"))
    item_id = TextElement(Tag("goods.nomenclature.item.id"))
    suffix = TextElement(Tag("productline.suffix"))


@Record.register_child("goods_nomenclature_description")
class GoodsNomenclatureDescriptionParser(Writable, ElementParser):
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
class GoodsNomenclatureDescriptionPeriodParser(Writable, ElementParser):
    tag = Tag("goods.nomenclature.description.period")

    goods_nomenclature_description_period_sid = TextElement(
        "goods.nomenclature.description.period.sid"
    )
    goods_nomenclature_sid = TextElement(Tag("goods.nomenclature.sid"))
    valid_between_lower = TextElement(Tag("validity.start.date"))
    goods_nomenclature_item_id = TextElement(Tag("goods.nomenclature.item.id"))
    productline_suffix = TextElement(Tag("productline.suffix"))


@Record.register_child("goods_nomenclature_indent")
class GoodsNomenclatureIndentsParser(ValidityMixin, Writable, ElementParser):
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
class FootnoteAssociationGoodsNomenclatureParser(
    ValidityMixin, Writable, ElementParser
):
    tag = Tag("footnote.association.goods.nomenclature")

    goods_nomenclature__sid = TextElement(Tag("goods.nomenclature.sid"))
    associated_footnote__footnote_id = TextElement(Tag("footnote.id"))
    associated_footnote__footnote_type_id = TextElement(Tag("footnote.type"))

    # valid_between_lower = TextElement(Tag("validity.start.date"))
    # valid_between_upper = TextElement(Tag("validity.end.date"))
