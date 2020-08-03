from importer.handlers import ElementHandler
from importer.handlers import TextElement
from importer.handlers import ValidityMixin
from importer.handlers import Writable
from importer.namespaces import Tag


class GoodsNomenclature(ValidityMixin, Writable, ElementHandler):
    tag = Tag("goods.nomenclature")
    sid = TextElement(Tag("goods.nomenclature.sid"))
    item_id = TextElement(Tag("goods.nomenclature.item.id"))
    productline_suffix = TextElement(Tag("producline.suffix"))  # XXX not a typo
    valid_between_lower = TextElement(Tag("validity.start.date"))
    statistical_indicator = TextElement(Tag("statistical.indicator"))


class GoodsNomenclatureDescription(Writable, ElementHandler):
    tag = Tag("goods.nomenclature.description")
    goods_nomenclature_description_period_sid = TextElement(
        "goods.nomenclature.description.period.sid"
    )
    language_id = TextElement(Tag("language.id"))
    goods_nomenclature_sid = TextElement(Tag("goods.nomenclature.sid"))
    goods_nomenclature_item_id = TextElement(Tag("goods.nomenclature.item.id"))
    productline_suffix = TextElement(Tag("productline.suffix"))
    description = TextElement(Tag("description"))


class GoodsNomenclatureDescriptionPeriod(Writable, ElementHandler):
    tag = Tag("goods.nomenclature.description.period")
    goods_nomenclature_description_period_sid = TextElement(
        "goods.nomenclature.description.period.sid"
    )
    goods_nomenclature_sid = TextElement(Tag("goods.nomenclature.sid"))
    valid_between_lower = TextElement(Tag("validity.start.date"))
    goods_nomenclature_item_id = TextElement(Tag("goods.nomenclature.item.id"))
    productline_suffix = TextElement(Tag("productline.suffix"))


class GoodsNomenclatureIndents(ValidityMixin, Writable, ElementHandler):
    tag = Tag("goods.nomenclature.indents")
    sid = TextElement(Tag("goods.nomenclature.indent.sid"))
    goods_nomenclature_sid = TextElement(Tag("goods.nomenclature.sid"))
    valid_between_lower = TextElement(Tag("validity.start.date"))
    number_indents = TextElement(Tag("number.indents"))
    goods_nomenclature_item_id = TextElement(Tag("goods.nomenclature.item.id"))
    productline_suffix = TextElement(Tag("productline.suffix"))


class GoodsNomenclatureOrigin(Writable, ElementHandler):
    tag = Tag("goods.nomenclature.origin")
    goods_nomenclature_sid = TextElement(Tag("goods.nomenclature.sid"))
    derived_goods_nomenclature_item_id = TextElement(
        "derived.goods.nomenclature.item.id"
    )
    derived_productline_suffix = TextElement(Tag("derived.productline.suffix"))
    goods_nomenclature_item_id = TextElement(Tag("goods.nomenclature.item.id"))
    productline_suffix = TextElement(Tag("productline.suffix"))
