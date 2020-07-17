from datetime import datetime

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils import timezone

from common.util import validity_range_contains_range

ITEM_ID_REGEX = r"\d{10}"
item_id_validator = RegexValidator(ITEM_ID_REGEX)

SUFFIX_REGEX = r"\d{2}"
suffix_validator = RegexValidator(SUFFIX_REGEX)


def validate_description_is_not_null(goods_description):
    if not goods_description.description:
        raise ValidationError({"description": "A description cannot be blank"})


def validate_goods_parent_validity_includes_good(goods_nomenclature_indent):
    """
    NIG2
    """
    goods_validity = goods_nomenclature_indent.indented_goods_nomenclature.valid_between
    parent = goods_nomenclature_indent.get_parent()

    if not parent:
        return
    parent_validity = parent.valid_between

    if not validity_range_contains_range(parent_validity, goods_validity):
        raise ValidationError(
            {
                "valid_between": "Parent Goods Nomenclature validity period must encompass "
                "the entire validity period of the Goods Nomenclature"
            }
        )


def validate_has_origin(goods_nomenclature):
    """
    NIG5

    Almost all goods nomenclatures must have an origin, excluding two scenarios:

        1) They are a top level code (depth/indent of 1)
        2) They were made before 2010-01-01 (legacy data)

    Therefore check for these two conditions, and if neither are met ensure an origin exists.
    """

    lower_bound = datetime(2010, 1, 1).replace(tzinfo=timezone.utc)

    if (
        goods_nomenclature.indents.filter(depth=1).exists()
        or goods_nomenclature.valid_between.lower <= lower_bound
    ):
        return
    if not goods_nomenclature.origin:
        raise ValidationError(
            {"origin": "Non top-level goods must have an origin specified."}
        )


def validate_predecessor_ends_before_successor_starts(goods_nomenclature):
    """
    NIG7

    By default the upper bound is exclusive whilst the lower bound is inclusive.
    So we just need to make sure the bounds match.
    """
    predecessor = goods_nomenclature.origin

    if not predecessor:
        return

    ends_on = predecessor.valid_between.upper
    starts_on = goods_nomenclature.valid_between.lower

    if ends_on is None or not ends_on == starts_on:
        raise ValidationError(
            {
                "valid_between": "Succeeding Goods Nomenclature must start the day after the origin ends"
            }
        )


def validate_at_least_one_indent(goods_nomenclature):
    """
    NIG11
    """
    indents = goods_nomenclature.indents.filter(
        workbasket__id__lte=goods_nomenclature.workbasket.id
    )
    if not indents.exists():
        raise ValidationError({"indents": "At least one indent record is mandatory."})

    if (
        indents.count() == 1
        and indents.first().valid_between.lower
        != goods_nomenclature.valid_between.lower
    ):
        raise ValidationError(
            {
                "indents": "The first indent start date must match the start date of the "
                "Goods Nomenclature."
            }
        )


def validate_indent_start_date_less_than_goods_end_date(goods_nomenclature_indent):
    """
    NIG11
    """
    indent_validity = goods_nomenclature_indent.valid_between
    goods_validity = goods_nomenclature_indent.indented_goods_nomenclature.valid_between

    if goods_validity.upper and indent_validity.lower > goods_validity.upper:
        raise ValidationError(
            {
                "valid_between": "An indents start date must be less than or equal to the "
                "Goods Nomenclatures end date."
            }
        )


def validate_at_least_one_description(goods_nomenclature):
    """
    NIG12
    """
    descriptions = goods_nomenclature.descriptions.filter(
        workbasket__id__lte=goods_nomenclature.workbasket.id
    )
    if not descriptions.exists():
        raise ValidationError(
            {"descriptions": "At least one description record is mandatory."}
        )

    if (
        descriptions.count() == 1
        and descriptions.first().valid_between.lower
        != goods_nomenclature.valid_between.lower
    ):
        raise ValidationError(
            {
                "descriptions": "The first descriptions start date must match the start date of the "
                "Goods Nomenclature."
            }
        )


def validate_goods_validity_includes_footnote_association(footnote_association):
    """
    NIG22
    """
    association_validity = footnote_association.valid_between
    goods_validity = footnote_association.goods_nomenclature.valid_between

    if not validity_range_contains_range(goods_validity, association_validity):
        raise ValidationError(
            {
                "valid_between": "Goods Nomenclature validity period must encompass "
                "the entire validity period of the Footnote association"
            }
        )


def validate_footnote_validity_includes_footnote_association(footnote_association):
    """
    NIG23
    """
    association_validity = footnote_association.valid_between
    footnote_validity = footnote_association.associated_footnote.valid_between

    if not validity_range_contains_range(footnote_validity, association_validity):
        raise ValidationError(
            {
                "valid_between": "Footnote validity period must encompass "
                "the entire validity period of the Footnote association"
            }
        )


def validate_duplicate_footnote_associations_cant_overlap(footnote_association):
    FootnoteAssociationGoodsNomenclature = footnote_association.__class__
    if FootnoteAssociationGoodsNomenclature.objects.filter(
        associated_footnote__footnote_id=footnote_association.associated_footnote.footnote_id,
        goods_nomenclature__sid=footnote_association.goods_nomenclature.sid,
        valid_between__overlap=footnote_association.valid_between,
    ).exists():
        raise ValidationError(
            {
                "valid_between": "Associations between the same Footnote and Goods Nomenclature "
                "must not have overlapping validity ranges."
            }
        )
