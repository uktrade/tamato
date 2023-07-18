from datetime import date

from commodities.import_handlers import *
from footnotes.models import FootnoteType
from importer.new_parsers import ModelLink
from importer.new_parsers import ModelLinkField
from importer.new_parsers import NewElementParser
from importer.parsers import NewChildPeriod
from importer.parsers import NewValidityMixin
from importer.parsers import NewWritable


class NewGoodsNomenclatureParser(NewValidityMixin, NewWritable, NewElementParser):
    # handler = GoodsNomenclatureHandler
    model = models.GoodsNomenclature
    record_code = "400"
    subrecord_code = "00"

    xml_object_tag = "goods.nomenclature"

    identity_fields = ["sid"]

    sid: str = None
    item_id: str = None
    suffix: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None
    statistical: str = None


class NewGoodsNomenclatureOriginParser(NewWritable, NewElementParser):
    # handler = GoodsNomenclatureOriginHandler
    model = models.GoodsNomenclatureOrigin

    model_links = [
        ModelLink(
            models.GoodsNomenclature,
            [
                ModelLinkField("new_goods_nomenclature__sid", "sid"),
                ModelLinkField("new_goods_nomenclature__item_id", "item_id"),
                ModelLinkField("new_goods_nomenclature__suffix", "suffix"),
            ],
            "goods.nomenclature",
        ),
        ModelLink(
            models.GoodsNomenclature,
            [
                ModelLinkField("new_goods_nomenclature__item_id", "item_id"),
                ModelLinkField("new_goods_nomenclature__suffix", "suffix"),
            ],
            "goods.nomenclature",
        ),
    ]

    record_code = "400"
    subrecord_code = "35"

    xml_object_tag = "goods.nomenclature.origin"

    new_goods_nomenclature__sid: str = None
    derived_from_goods_nomenclature__item_id: str = None
    derived_from_goods_nomenclature__suffix: str = None
    new_goods_nomenclature__item_id: str = None
    new_goods_nomenclature__suffix: str = None


class NewGoodsNomenclatureSuccessorParser(NewWritable, NewElementParser):
    # handler = GoodsNomenclatureSuccessorHandler
    model = models.GoodsNomenclatureSuccessor

    model_links = [
        ModelLink(
            models.GoodsNomenclature,
            [
                ModelLinkField("replaced_goods_nomenclature__sid", "sid"),
            ],
            "goods.nomenclature",
        ),
        ModelLink(
            models.GoodsNomenclature,
            [
                ModelLinkField("absorbed_into_goods_nomenclature__item_id", "item_id"),
                ModelLinkField("absorbed_into_goods_nomenclature__suffix", "suffix"),
            ],
            "goods.nomenclature",
        ),
        ModelLink(
            models.GoodsNomenclature,
            [
                ModelLinkField("replaced_goods_nomenclature__item_id", "item_id"),
                ModelLinkField("replaced_goods_nomenclature__suffix", "suffix"),
            ],
            "goods.nomenclature",
        ),
    ]

    record_code = "400"
    subrecord_code = "40"

    xml_object_tag = "goods.nomenclature.successor"

    replaced_goods_nomenclature__sid: str = None
    absorbed_into_goods_nomenclature__item_id: str = None
    absorbed_into_goods_nomenclature__suffix: str = None
    replaced_goods_nomenclature__item_id: str = None
    replaced_goods_nomenclature__suffix: str = None


class NewGoodsNomenclatureDescriptionParser(NewWritable, NewElementParser):
    # handler = GoodsNomenclatureDescriptionHandler
    model = models.GoodsNomenclatureDescription

    model_links = [
        ModelLink(
            models.GoodsNomenclature,
            [
                ModelLinkField("described_goods_nomenclature__sid", "sid"),
                ModelLinkField("described_goods_nomenclature__item_id", "item_id"),
                ModelLinkField("described_goods_nomenclature__suffix", "suffix"),
            ],
            "goods.nomenclature",
        ),
    ]

    record_code = "400"
    subrecord_code = "15"

    xml_object_tag = "goods.nomenclature.description"

    sid: str = None
    # language_id: str = None
    described_goods_nomenclature__sid: str = None
    described_goods_nomenclature__item_id: str = None
    described_goods_nomenclature__suffix: str = None
    description: str = None


class NewGoodsNomenclatureDescriptionPeriodParser(
    NewWritable,
    NewElementParser,
    NewChildPeriod,
):
    model = models.GoodsNomenclatureDescription
    parent_parser = NewGoodsNomenclatureDescriptionParser

    model_links = [
        ModelLink(
            models.GoodsNomenclature,
            [
                ModelLinkField("described_goods_nomenclature__sid", "sid"),
                ModelLinkField("described_goods_nomenclature__item_id", "item_id"),
                ModelLinkField("described_goods_nomenclature__suffix", "suffix"),
            ],
            "goods.nomenclature",
        ),
        ModelLink(
            models.GoodsNomenclatureDescription,
            [
                ModelLinkField("goods_nomenclature_description_period__sid", "sid"),
            ],
            "goods.nomenclature.description",
        ),
    ]

    value_mapping = {
        "goods_nomenclature_description_period_sid": "sid",
    }

    record_code = "400"
    subrecord_code = "10"

    xml_object_tag = "goods.nomenclature.description.period"

    sid: str = None
    described_goods_nomenclature__sid: str = None
    described_goods_nomenclature__item_id: str = None
    described_goods_nomenclature__suffix: str = None
    validity_start: date = None


class NewGoodsNomenclatureIndentParser(NewWritable, NewElementParser):
    model = models.GoodsNomenclatureIndent

    model_links = [
        ModelLink(
            models.GoodsNomenclature,
            [
                ModelLinkField("described_goods_nomenclature__sid", "sid"),
                ModelLinkField("described_goods_nomenclature__item_id", "item_id"),
                ModelLinkField("described_goods_nomenclature__suffix", "suffix"),
            ],
            "goods.nomenclature",
        ),
    ]

    record_code = "400"
    subrecord_code = "05"

    xml_object_tag = "goods.nomenclature.indents"

    sid: str = None
    indented_goods_nomenclature__sid: str = None
    validity_start: date = None
    indent: str = None
    indented_goods_nomenclature__item_id: str = None
    indented_goods_nomenclature__suffix: str = None


class NewFootnoteAssociationGoodsNomenclatureParser(
    NewValidityMixin,
    NewWritable,
    NewElementParser,
):
    model = models.FootnoteAssociationGoodsNomenclature

    model_links = [
        ModelLink(
            models.GoodsNomenclature,
            [
                ModelLinkField("goods_nomenclature__sid", "sid"),
                ModelLinkField("goods_nomenclature__item_id", "item_id"),
                ModelLinkField("goods_nomenclature__suffix", "suffix"),
            ],
            "goods.nomenclature",
        ),
        ModelLink(
            FootnoteType,
            [
                ModelLinkField(
                    "associated_footnote__footnote_type__footnote_type_id",
                    "footnote_type_id",
                ),
            ],
            "footnote.type",
        ),
        ModelLink(
            Footnote,
            [
                ModelLinkField("associated_footnote__footnote_id", "footnote_id"),
            ],
            "footnote",
        ),
    ]

    record_code = "400"
    subrecord_code = "20"

    xml_object_tag = "footnote.association.goods.nomenclature"

    goods_nomenclature__sid: str = None
    associated_footnote__footnote_type__footnote_type_id: str = None
    associated_footnote__footnote_id: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None
    goods_nomenclature__item_id: str = None
    goods_nomenclature__suffix: str = None
