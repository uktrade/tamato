"""Business rules for commodities/goods nomenclatures."""
from datetime import datetime
from datetime import timedelta
from datetime import timezone

from common.business_rules import BusinessRule
from common.business_rules import find_duplicate_start_dates
from common.business_rules import PreventDeleteIfInUse
from common.business_rules import ValidityPeriodContained
from common.util import validity_range_contains_range
from common.validators import UpdateType


class NIG1(BusinessRule):
    """The validity period of the goods nomenclature must not overlap any other goods
    nomenclature with the same SID.
    """

    def validate(self, good):
        if (
            type(good)
            .objects.filter(
                sid=good.sid,
                valid_between__overlap=good.valid_between,
            )
            .exists()
        ):
            raise self.violation(good)


class NIG2(BusinessRule):
    """The validity period of the goods nomenclature must be within the validity period
    of the product line above in the hierarchy.
    """

    def validate(self, indent):
        goods_validity = indent.indented_goods_nomenclature.valid_between

        for node in indent.nodes.all():
            parent = node.get_parent()

            if not parent:
                continue

            parent_validity = parent.indent.indented_goods_nomenclature.valid_between

            if not validity_range_contains_range(parent_validity, goods_validity):
                raise self.violation(indent)


class NIG5(BusinessRule):
    """When creating a goods nomenclature code, an origin must exist. This rule is only
    applicable to update extractions.
    """

    def validate(self, good):
        """Almost all goods nomenclatures must have an origin, excluding two scenarios:

            1) They are a top level code (depth/indent of 1)
            2) They were made before 2010-01-01 (legacy data)

        Therefore check for these two conditions, and if neither are met ensure an origin exists.
        """

        lower_bound = datetime(2010, 1, 1).replace(tzinfo=timezone.utc)

        if not (
            good.valid_between.lower <= lower_bound
            or good.indents.filter(nodes__depth=1).exists()
            or good.origins.exists()
        ):
            raise self.violation("Non top-level goods must have an origin specified.")


class NIG7(BusinessRule):
    """The origin must be applicable the day before the start date of the new code
    entered.
    """

    def validate(self, origin):
        """By default the upper bound is exclusive whilst the lower bound is inclusive.
        So we just need to make sure the bounds match.
        """

        origin_range = origin.derived_from_goods_nomenclature.valid_between
        starts_on = origin.new_goods_nomenclature.valid_between.lower
        day_before_start = starts_on - timedelta(days=1)

        if day_before_start not in origin_range:
            raise self.violation(
                f'GoodsNomenclatureOrigin {origin}: The "derived from" code, if '
                "entered, must be a goods nomenclature which exists and is applicable "
                "the day before the start date of the new code entered. "
                f"Origin {origin_range} is not applicable on {day_before_start}."
            )


class NIG10(BusinessRule):
    """The successor must be applicable the day after the end date of the old code."""

    def validate(self, successor):
        ends_on = successor.replaced_goods_nomenclature.valid_between.upper
        successor_range = successor.absorbed_into_goods_nomenclature.valid_between

        if ends_on is None:
            raise self.violation(
                f"GoodsNomenclatureSuccessor {successor}: A successor can only be added "
                "for goods nomenclature codes with a closing date."
            )

        day_after_end = ends_on + timedelta(days=1)
        if day_after_end not in successor_range:
            raise self.violation(
                f'GoodsNomenclatureSuccessor {successor}: The "absorbed by" code, if '
                "entered, must be a goods nomenclature which exists and is applicable "
                "the day after the closing date."
                f"Successor {successor_range} is not applicable on {day_after_end}."
            )


class NIG11(BusinessRule):
    """At least one indent record is mandatory. The start date of the first indentation
    must be equal to the start date of the nomenclature. No two associated indentations
    may have the same start date. The start date must be less than or equal to the end
    date of the nomenclature.
    """

    def validate(self, good):
        indents = good.indents.order_by("valid_between")

        if indents.count() < 1:
            raise self.violation(
                f"GoodsNomenclature {good}: At least one indent record is mandatory."
            )

        if indents.first().valid_between.lower != good.valid_between.lower:
            raise self.violation(
                f"GoodsNomenclature {good}: The start date of the first indentation must "
                "be equal to the start date of the nomenclature."
            )

        if find_duplicate_start_dates(indents).exists():
            raise self.violation(
                f"GoodsNomenclature {good}: No two associated indentations may have the "
                "same start date"
            )

        if indents.filter(valid_between__fully_gt=good.valid_between).exists():
            raise self.violation(
                f"GoodsNomenclature {good}: The start date of an associated indentation "
                "must be less than or equal to the end date of the nomenclature."
            )


class NIG12(BusinessRule):
    """At least one description is mandatory. The start date of the first description
    period must be equal to the start date of the nomenclature. No two associated
    description periods may have the same start date. The start date must be less than
    or equal to the end date of the nomenclature.
    """

    def validate(self, good):
        descriptions = good.descriptions.order_by("valid_between")

        if descriptions.count() < 1:
            raise self.violation(
                f"GoodsNomenclature {good}: At least one description record is mandatory."
            )

        if descriptions.first().valid_between.lower != good.valid_between.lower:
            raise self.violation(
                f"GoodsNomenclature {good}: The start date of the first description must "
                "be equal to the start date of the nomenclature."
            )

        if find_duplicate_start_dates(descriptions).exists():
            raise self.violation(
                f"GoodsNomenclature {good}: No two associated descriptions may have the "
                "same start date"
            )

        if descriptions.filter(valid_between__fully_gt=good.valid_between).exists():
            raise self.violation(
                f"GoodsNomenclature {good}: The start date of a description must be less "
                "than or equal to the end date of the nomenclature."
            )


class NIG22(ValidityPeriodContained):
    """The period of the association with a footnote must be within the validity period
    of the nomenclature.
    """

    container_field_name = "goods_nomenclature"


class NIG23(ValidityPeriodContained):
    """The period of the association with a footnote must be within the validity period
    of the footnote.
    """

    container_field_name = "associated_footnote"


class NIG24(BusinessRule):
    """When the same footnote is associated more than once with the same nomenclature
    then there may be no overlap in their association periods.
    """

    def validate(self, association):
        # XXX does this handle versions?
        overlapping = (
            type(association)
            .objects.filter(
                associated_footnote__footnote_id=association.associated_footnote.footnote_id,
                associated_footnote__footnote_type__footnote_type_id=association.associated_footnote.footnote_type.footnote_type_id,
                goods_nomenclature__sid=association.goods_nomenclature.sid,
                valid_between__overlap=association.valid_between,
            )
            .exclude(
                id=association.pk,
            )
        )

        if overlapping.exists():
            raise self.violation(association)


class NIG30(BusinessRule):
    """When a goods nomenclature is used in a goods measure then the validity period of
    the goods nomenclature must span the validity period of the goods measure.
    """

    def validate(self, good):
        if (
            good.measures.model.objects.filter(goods_nomenclature__sid=good.sid)
            .exclude(valid_between__contained_by=good.valid_between)
            .exists()
        ):
            raise self.violation(good)


class NIG31(BusinessRule):
    """When a goods nomenclature is used in an additional nomenclature measure then the
    validity period of the goods nomenclature must span the validity period of the
    additional nomenclature measure.
    """

    def validate(self, good):
        # XXX is this the correct interpretation?
        if (
            good.measures.model.objects.filter(goods_nomenclature__sid=good.sid)
            .filter(additional_code__isnull=False)
            .exclude(additional_code__valid_between__contained_by=good.valid_between)
            .exists()
        ):
            raise self.violation(good)


class NIG34(PreventDeleteIfInUse):
    """A goods nomenclature cannot be deleted if it is used in a goods measure."""


class NIG35(BusinessRule):
    """A goods nomenclature cannot be deleted if it is used in an additional
    nomenclature measure.
    """

    # XXX this is redundant - NIG34 will be violated first

    def validate(self, good):
        if good.update_type != UpdateType.DELETE:
            return

        if good.measures.model.objects.filter(
            goods_nomenclature__sid=good.sid,
            additional_code__isnull=False,
        ).exists():
            raise self.violation(good)
