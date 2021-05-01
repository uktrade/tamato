import logging

from importer.namespaces import Tag
from importer.parsers import ElementParser
from importer.parsers import TextElement
from importer.parsers import ValidityMixin
from importer.parsers import ValidityStartMixin
from importer.parsers import Writable
from importer.taric import RecordParser

logger = logging.getLogger(__name__)


@RecordParser.register_child("goods_nomenclature")
class GoodsNomenclatureParser(ValidityMixin, Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="goods.nomenclature" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="goods.nomenclature.sid" type="SID"/>
                    <xs:element name="goods.nomenclature.item.id" type="GoodsNomenclatureItemId"/>
                    <xs:element name="producline.suffix" type="ProductLineSuffix"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                    <xs:element name="statistical.indicator" type="StatisticalIndicator"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    tag = Tag("goods.nomenclature")

    sid = TextElement(Tag("goods.nomenclature.sid"))
    item_id = TextElement(Tag("goods.nomenclature.item.id"))
    suffix = TextElement(Tag("producline.suffix"))  # XXX not a typo
    valid_between_lower = TextElement(Tag("validity.start.date"))
    valid_between_upper = TextElement(Tag("validity.end.date"))
    statistical = TextElement(Tag("statistical.indicator"))


@RecordParser.register_child("goods_nomenclature_origin")
class GoodsNomenclatureOriginParser(Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="goods.nomenclature.origin" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="goods.nomenclature.sid" type="SID"/>
                    <xs:element name="derived.goods.nomenclature.item.id" type="GoodsNomenclatureItemId"/>
                    <xs:element name="derived.productline.suffix" type="ProductLineSuffix"/>
                    <xs:element name="goods.nomenclature.item.id" type="GoodsNomenclatureItemId"/>
                    <xs:element name="productline.suffix" type="ProductLineSuffix"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    tag = Tag("goods.nomenclature.origin")

    new_goods_nomenclature__sid = TextElement(Tag("goods.nomenclature.sid"))
    derived_from_goods_nomenclature__item_id = TextElement(
        Tag("derived.goods.nomenclature.item.id"),
    )
    derived_from_goods_nomenclature__suffix = TextElement(
        Tag("derived.productline.suffix"),
    )
    new_goods_nomenclature__item_id = TextElement(Tag("goods.nomenclature.item.id"))
    new_goods_nomenclature__suffix = TextElement(Tag("productline.suffix"))


@RecordParser.register_child("goods_nomenclature_successor")
class GoodsNomenclatureSuccessorParser(Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="goods.nomenclature.successor" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="goods.nomenclature.sid" type="SID"/>
                    <xs:element name="absorbed.goods.nomenclature.item.id" type="GoodsNomenclatureItemId"/>
                    <xs:element name="absorbed.productline.suffix" type="ProductLineSuffix"/>
                    <xs:element name="goods.nomenclature.item.id" type="GoodsNomenclatureItemId"/>
                    <xs:element name="productline.suffix" type="ProductLineSuffix"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    tag = Tag("goods.nomenclature.successor")

    replaced_goods_nomenclature__sid = TextElement(Tag("goods.nomenclature.sid"))
    absorbed_into_goods_nomenclature__item_id = TextElement(
        Tag("absorbed.goods.nomenclature.item.id"),
    )
    absorbed_into_goods_nomenclature__suffix = TextElement(
        Tag("absorbed.productline.suffix"),
    )
    replaced_goods_nomenclature__item_id = TextElement(
        Tag("goods.nomenclature.item.id"),
    )
    replaced_goods_nomenclature__suffix = TextElement(Tag("productline.suffix"))


@RecordParser.register_child("goods_nomenclature_description")
class GoodsNomenclatureDescriptionParser(Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="goods.nomenclature.description" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="goods.nomenclature.description.period.sid" type="SID"/>
                    <xs:element name="language.id" type="LanguageId"/>
                    <xs:element name="goods.nomenclature.sid" type="SID"/>
                    <xs:element name="goods.nomenclature.item.id" type="GoodsNomenclatureItemId"/>
                    <xs:element name="productline.suffix" type="ProductLineSuffix"/>
                    <xs:element name="description" type="LongDescription" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    tag = Tag("goods.nomenclature.description")

    sid = TextElement(Tag("goods.nomenclature.description.period.sid"))
    language_id = TextElement(Tag("language.id"))
    described_goods_nomenclature__sid = TextElement(Tag("goods.nomenclature.sid"))
    described_goods_nomenclature__item_id = TextElement(
        Tag("goods.nomenclature.item.id"),
    )
    described_goods_nomenclature__productline_suffix = TextElement(
        Tag("productline.suffix"),
    )
    description = TextElement(Tag("description"))


@RecordParser.register_child("goods_nomenclature_description_period")
class GoodsNomenclatureDescriptionPeriodParser(
    ValidityStartMixin,
    Writable,
    ElementParser,
):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="goods.nomenclature.description.period" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="goods.nomenclature.description.period.sid" type="SID"/>
                    <xs:element name="goods.nomenclature.sid" type="SID"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="goods.nomenclature.item.id" type="GoodsNomenclatureItemId"/>
                    <xs:element name="productline.suffix" type="ProductLineSuffix"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    tag = Tag("goods.nomenclature.description.period")

    sid = TextElement(Tag("goods.nomenclature.description.period.sid"))
    described_goods_nomenclature__sid = TextElement(Tag("goods.nomenclature.sid"))
    described_goods_nomenclature__item_id = TextElement(
        Tag("goods.nomenclature.item.id"),
    )
    described_goods_nomenclature__productline_suffix = TextElement(
        Tag("productline.suffix"),
    )


@RecordParser.register_child("goods_nomenclature_indent")
class GoodsNomenclatureIndentsParser(ValidityStartMixin, Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="goods.nomenclature.indents" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="goods.nomenclature.indent.sid" type="SID"/>
                    <xs:element name="goods.nomenclature.sid" type="SID"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="number.indents" type="NumberOf"/>
                    <xs:element name="goods.nomenclature.item.id" type="GoodsNomenclatureItemId"/>
                    <xs:element name="productline.suffix" type="ProductLineSuffix"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    tag = Tag("goods.nomenclature.indents")

    sid = TextElement(Tag("goods.nomenclature.indent.sid"))
    indented_goods_nomenclature__sid = TextElement(Tag("goods.nomenclature.sid"))
    indent = TextElement(Tag("number.indents"))
    indented_goods_nomenclature__item_id = TextElement(
        Tag("goods.nomenclature.item.id"),
    )
    indented_goods_nomenclature__suffix = TextElement(Tag("productline.suffix"))


@RecordParser.register_child("footnote_association_goods_nomenclature")
class FootnoteAssociationGoodsNomenclatureParser(
    ValidityMixin,
    Writable,
    ElementParser,
):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="footnote.association.goods.nomenclature" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="goods.nomenclature.sid" type="SID"/>
                    <xs:element name="footnote.type" type="FootnoteTypeId"/>
                    <xs:element name="footnote.id" type="FootnoteId"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                    <xs:element name="goods.nomenclature.item.id" type="GoodsNomenclatureItemId"/>
                    <xs:element name="productline.suffix" type="ProductLineSuffix"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    tag = Tag("footnote.association.goods.nomenclature")

    goods_nomenclature__sid = TextElement(Tag("goods.nomenclature.sid"))
    associated_footnote__footnote_id = TextElement(Tag("footnote.id"))
    associated_footnote__footnote_type__footnote_type_id = TextElement(
        Tag("footnote.type"),
    )
