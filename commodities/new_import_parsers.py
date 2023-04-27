from datetime import date

from importer.new_parsers import NewElementParser
from importer.parsers import ElementParser
from importer.parsers import NewValidityMixin
from importer.parsers import NewWritable
from importer.parsers import ValidityMixin
from importer.parsers import Writable


class NewGoodsNomenclatureParser(NewValidityMixin, NewWritable, NewElementParser):
    record_code = "400"
    subrecord_code = "00"

    xml_object_tag = "goods.nomenclature"

    sid: str = None
    item_id: str = None
    suffix: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None
    statistical: str = None


class NewGoodsNomenclatureOriginParser(NewWritable, NewElementParser):
    record_code = "400"
    subrecord_code = "35"

    xml_object_tag = "goods.nomenclature.origin"

    new_goods_nomenclature__sid: str = None
    derived_from_goods_nomenclature__item_id: str = None
    derived_from_goods_nomenclature__suffix: str = None
    new_goods_nomenclature__item_id: str = None
    new_goods_nomenclature__suffix: str = None


class NewGoodsNomenclatureSuccessorParser(NewWritable, NewElementParser):
    record_code = "400"
    subrecord_code = "40"

    xml_object_tag = "goods.nomenclature.successor"

    replaced_goods_nomenclature__sid: str = None
    absorbed_into_goods_nomenclature__item_id: str = None
    absorbed_into_goods_nomenclature__suffix: str = None
    replaced_goods_nomenclature__item_id: str = None
    replaced_goods_nomenclature__suffix: str = None


class NewGoodsNomenclatureDescriptionParser(NewWritable, NewElementParser):
    record_code = "400"
    subrecord_code = "15"

    xml_object_tag = "goods.nomenclature.description"

    sid: str = None
    language_id: str = None
    described_goods_nomenclature__sid: str = None
    described_goods_nomenclature__item_id: str = None
    described_goods_nomenclature__suffix: str = None
    description: str = None


class NewGoodsNomenclatureDescriptionPeriodParser(NewWritable, NewElementParser):
    record_code = "400"
    subrecord_code = "10"

    xml_object_tag = "goods.nomenclature.description.period"

    sid: str = None
    described_goods_nomenclature__sid: str = None
    validity_start: date = None
    described_goods_nomenclature__item_id: str = None
    described_goods_nomenclature__suffix: str = None


class NewGoodsNomenclatureIndentParser(NewWritable, NewElementParser):
    record_code = "400"
    subrecord_code = "05"

    xml_object_tag = "goods.nomenclature.indents"

    sid: str = None
    indented_goods_nomenclature__sid: str = None
    validity_start: date = None
    indent: str = None
    indented_goods_nomenclature__item_id: str = None
    indented_goods_nomenclature__suffix: str = None


class FootnoteAssociationGoodsNomenclatureParser(
    ValidityMixin,
    Writable,
    ElementParser,
):
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
