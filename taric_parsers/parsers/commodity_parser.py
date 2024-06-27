from datetime import date

from commodities.models import FootnoteAssociationGoodsNomenclature
from commodities.models import GoodsNomenclature
from commodities.models import GoodsNomenclatureDescription
from commodities.models import GoodsNomenclatureIndent
from commodities.models import GoodsNomenclatureOrigin
from commodities.models import GoodsNomenclatureSuccessor
from footnotes.models import Footnote
from taric_parsers.parser_model_link import ModelLink
from taric_parsers.parser_model_link import ModelLinkField
from taric_parsers.parsers.mixins import ChildPeriod
from taric_parsers.parsers.mixins import ValidityMixin
from taric_parsers.parsers.mixins import Writable
from taric_parsers.parsers.taric_parser import BaseTaricParser


class GoodsNomenclatureParserV2(Writable, BaseTaricParser):
    model = GoodsNomenclature

    model_links = []
    value_mapping = {
        "goods_nomenclature_sid": "sid",
        "goods_nomenclature_item_id": "item_id",
        "producline_suffix": "suffix",
        "validity_start_date": "valid_between_lower",
        "validity_end_date": "valid_between_upper",
        "statistical_indicator": "statistical",
    }

    record_code = "400"
    subrecord_code = "00"

    xml_object_tag = "goods.nomenclature"

    identity_fields = ["sid", "item_id", "suffix"]

    sid: int = None
    item_id: str = None
    suffix: int = None
    valid_between_lower: date = None
    valid_between_upper: date = None
    statistical: int = None


class GoodsNomenclatureOriginParserV2(Writable, BaseTaricParser):
    model = GoodsNomenclatureOrigin

    model_links = [
        ModelLink(
            GoodsNomenclature,
            [
                ModelLinkField("new_goods_nomenclature__sid", "sid"),
                ModelLinkField("new_goods_nomenclature__item_id", "item_id"),
                ModelLinkField("new_goods_nomenclature__suffix", "suffix"),
            ],
            "goods.nomenclature",
        ),
        ModelLink(
            GoodsNomenclature,
            [
                ModelLinkField("derived_from_goods_nomenclature__item_id", "item_id"),
                ModelLinkField("derived_from_goods_nomenclature__suffix", "suffix"),
            ],
            "goods.nomenclature",
        ),
    ]

    value_mapping = {
        "goods_nomenclature_sid": "new_goods_nomenclature__sid",
        "goods_nomenclature_item_id": "new_goods_nomenclature__item_id",
        "derived_goods_nomenclature_sid": "derived_from_goods_nomenclature__sid",
        "derived_goods_nomenclature_item_id": "derived_from_goods_nomenclature__item_id",
        "productline_suffix": "new_goods_nomenclature__suffix",
        "derived_productline_suffix": "derived_from_goods_nomenclature__suffix",
    }

    record_code = "400"
    subrecord_code = "35"

    xml_object_tag = "goods.nomenclature.origin"

    identity_fields = [
        "new_goods_nomenclature__sid",
        "new_goods_nomenclature__item_id",
        "new_goods_nomenclature__suffix",
        "derived_from_goods_nomenclature__item_id",
        "derived_from_goods_nomenclature__suffix",
    ]

    updates_allowed = False

    new_goods_nomenclature__sid: int = None
    new_goods_nomenclature__item_id: str = None
    new_goods_nomenclature__suffix: int = None
    derived_from_goods_nomenclature__item_id: str = None
    derived_from_goods_nomenclature__suffix: int = None


class GoodsNomenclatureSuccessorParserV2(Writable, BaseTaricParser):
    model = GoodsNomenclatureSuccessor

    model_links = [
        ModelLink(
            GoodsNomenclature,
            [
                ModelLinkField("replaced_goods_nomenclature__sid", "sid"),
                ModelLinkField("replaced_goods_nomenclature__item_id", "item_id"),
                ModelLinkField("replaced_goods_nomenclature__suffix", "suffix"),
            ],
            "goods.nomenclature",
        ),
        ModelLink(
            GoodsNomenclature,
            [
                ModelLinkField("absorbed_into_goods_nomenclature__item_id", "item_id"),
                ModelLinkField("absorbed_into_goods_nomenclature__suffix", "suffix"),
            ],
            "goods.nomenclature",
        ),
    ]

    value_mapping = {
        "goods_nomenclature_sid": "replaced_goods_nomenclature__sid",
        "goods_nomenclature_item_id": "replaced_goods_nomenclature__item_id",
        "productline_suffix": "replaced_goods_nomenclature__suffix",
        "absorbed_goods_nomenclature_item_id": "absorbed_into_goods_nomenclature__item_id",
        "absorbed_productline_suffix": "absorbed_into_goods_nomenclature__suffix",
    }

    record_code = "400"
    subrecord_code = "40"

    xml_object_tag = "goods.nomenclature.successor"

    identity_fields = [
        "replaced_goods_nomenclature__sid",
        "replaced_goods_nomenclature__item_id",
        "replaced_goods_nomenclature__suffix",
        "absorbed_into_goods_nomenclature__item_id",
        "absorbed_into_goods_nomenclature__suffix",
    ]

    updates_allowed = False

    replaced_goods_nomenclature__sid: int = None
    replaced_goods_nomenclature__item_id: str = None
    replaced_goods_nomenclature__suffix: int = None
    absorbed_into_goods_nomenclature__item_id: str = None
    absorbed_into_goods_nomenclature__suffix: int = None


class GoodsNomenclatureDescriptionParserV2(Writable, BaseTaricParser):
    model = GoodsNomenclatureDescription

    model_links = [
        ModelLink(
            GoodsNomenclature,
            [
                ModelLinkField("described_goods_nomenclature__sid", "sid"),
                ModelLinkField("described_goods_nomenclature__item_id", "item_id"),
                ModelLinkField("described_goods_nomenclature__suffix", "suffix"),
            ],
            "goods.nomenclature",
        ),
    ]

    # from field name (coming from XML) : to field name on this object
    value_mapping = {
        "goods_nomenclature_description_period_sid": "sid",
        "goods_nomenclature_sid": "described_goods_nomenclature__sid",
        "goods_nomenclature_item_id": "described_goods_nomenclature__item_id",
        "productline_suffix": "described_goods_nomenclature__suffix",
    }

    record_code = "400"
    subrecord_code = "15"

    xml_object_tag = "goods.nomenclature.description"

    identity_fields = [
        "sid",
        "described_goods_nomenclature__sid",
        "described_goods_nomenclature__item_id",
        "described_goods_nomenclature__suffix",
    ]

    sid: int = None
    # language_id: str = None
    described_goods_nomenclature__sid: int = None
    described_goods_nomenclature__item_id: str = None
    described_goods_nomenclature__suffix: int = None
    description: str = None
    allow_update_without_children = True
    skip_identity_check = True


class GoodsNomenclatureDescriptionPeriodParserV2(
    Writable,
    BaseTaricParser,
    ChildPeriod,
):
    model = GoodsNomenclatureDescription
    parent_parser = GoodsNomenclatureDescriptionParserV2

    model_links = [
        ModelLink(
            GoodsNomenclature,
            [
                ModelLinkField("described_goods_nomenclature__sid", "sid"),
                ModelLinkField("described_goods_nomenclature__item_id", "item_id"),
                ModelLinkField("described_goods_nomenclature__suffix", "suffix"),
            ],
            "goods.nomenclature",
        ),
        ModelLink(
            GoodsNomenclatureDescription,
            [
                ModelLinkField("sid", "sid"),
            ],
            "goods.nomenclature.description",
        ),
    ]

    value_mapping = {
        "goods_nomenclature_description_period_sid": "sid",
        "goods_nomenclature_sid": "described_goods_nomenclature__sid",
        "goods_nomenclature_item_id": "described_goods_nomenclature__item_id",
        "productline_suffix": "described_goods_nomenclature__suffix",
        "validity_start_date": "validity_start",
    }

    deletes_allowed = False

    identity_fields = ["sid"]

    record_code = "400"
    subrecord_code = "10"

    xml_object_tag = "goods.nomenclature.description.period"

    sid: int = None
    described_goods_nomenclature__sid: int = None
    described_goods_nomenclature__item_id: str = None
    described_goods_nomenclature__suffix: int = None
    validity_start: date = None


class GoodsNomenclatureIndentParserV2(Writable, BaseTaricParser):
    model = GoodsNomenclatureIndent

    model_links = [
        ModelLink(
            GoodsNomenclature,
            [
                ModelLinkField("indented_goods_nomenclature__sid", "sid"),
                ModelLinkField("indented_goods_nomenclature__item_id", "item_id"),
                ModelLinkField("indented_goods_nomenclature__suffix", "suffix"),
            ],
            "goods.nomenclature",
        ),
    ]

    value_mapping = {
        "goods_nomenclature_indent_sid": "sid",
        "goods_nomenclature_sid": "indented_goods_nomenclature__sid",
        "goods_nomenclature_item_id": "indented_goods_nomenclature__item_id",
        "productline_suffix": "indented_goods_nomenclature__suffix",
        "validity_start_date": "validity_start",
        "number_indents": "indent",
    }

    record_code = "400"
    subrecord_code = "05"

    xml_object_tag = "goods.nomenclature.indents"

    identity_fields = ["sid"]

    sid: int = None
    indented_goods_nomenclature__sid: int = None
    indented_goods_nomenclature__item_id: str = None
    indented_goods_nomenclature__suffix: int = None
    validity_start: date = None
    indent: int = None


class FootnoteAssociationGoodsNomenclatureParserV2(
    ValidityMixin,
    Writable,
    BaseTaricParser,
):
    model = FootnoteAssociationGoodsNomenclature

    model_links = [
        ModelLink(
            GoodsNomenclature,
            [
                ModelLinkField("goods_nomenclature__sid", "sid"),
                ModelLinkField("goods_nomenclature__item_id", "item_id"),
                ModelLinkField("goods_nomenclature__suffix", "suffix"),
            ],
            "goods.nomenclature",
        ),
        ModelLink(
            Footnote,
            [
                ModelLinkField("associated_footnote__footnote_id", "footnote_id"),
                ModelLinkField(
                    "associated_footnote__footnote_type__footnote_type_id",
                    "footnote_type__footnote_type_id",
                ),
            ],
            "footnote",
        ),
    ]

    value_mapping = {
        "goods_nomenclature_sid": "goods_nomenclature__sid",
        "footnote_type": "associated_footnote__footnote_type__footnote_type_id",
        "footnote_id": "associated_footnote__footnote_id",
        "validity_start_date": "valid_between_lower",
        "validity_end_date": "valid_between_upper",
        "goods_nomenclature_item_id": "goods_nomenclature__item_id",
        "productline_suffix": "goods_nomenclature__suffix",
    }

    record_code = "400"
    subrecord_code = "20"

    xml_object_tag = "footnote.association.goods.nomenclature"

    identity_fields = [
        "goods_nomenclature__sid",
        "goods_nomenclature__item_id",
        "goods_nomenclature__suffix",
        "associated_footnote__footnote_id",
    ]

    goods_nomenclature__sid: int = None
    goods_nomenclature__item_id: str = None
    goods_nomenclature__suffix: int = None
    associated_footnote__footnote_type__footnote_type_id: int = None
    associated_footnote__footnote_id: int = None
    valid_between_lower: date = None
    valid_between_upper: date = None
