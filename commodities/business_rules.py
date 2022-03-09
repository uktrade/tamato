"""Business rules for commodities/goods nomenclatures."""
import logging
from datetime import date
from datetime import timedelta

from common.business_rules import BusinessRule
from common.business_rules import DescriptionsRules
from common.business_rules import FootnoteApplicability
from common.business_rules import NoOverlapping
from common.business_rules import PreventDeleteIfInUse
from common.business_rules import ValidityPeriodContained
from common.business_rules import ValidityStartDateRules
from common.business_rules import only_applicable_after
from common.business_rules import skip_when_deleted
from common.business_rules import skip_when_not_deleted
from common.models.trackedmodel import TrackedModel
from common.util import validity_range_contains_range


class NIG1(NoOverlapping):
    """The validity period of the goods nomenclature must not overlap any other
    goods nomenclature with the same SID."""


class NIG2(BusinessRule):
    """The validity period of the goods nomenclature must be within the validity
    period of the product line above in the hierarchy."""

    # Note that a complete reading of this rule implies that a commodity's
    # parent should span the commodity but also that the commodity should span
    # all of it's children. However, the latter case is often broken by the EU
    # and not enforced by CDS. Therefore, we only check the parent case.
    #
    # Note that this means that running this business rule against a child can
    # therefore result in a violation. We think this is a feature and not a bug
    # because it allows parents to shift around without having to re-send all of
    # the data associated with the rest of the tree.

    def __init__(self, transaction=None):
        super().__init__(transaction)
        self.logger = logging.getLogger(type(self).__name__)

    def parent_spans_child(self, parent, child) -> bool:
        parent_validity = parent.indented_goods_nomenclature.version_at(
            self.transaction,
        ).valid_between
        child_validity = child.indented_goods_nomenclature.version_at(
            self.transaction,
        ).valid_between
        return validity_range_contains_range(parent_validity, child_validity)

    def validate(self, indent):
        from commodities.models.dc import Commodity
        from commodities.models.dc import get_chapter_collection

        try:
            good = indent.indented_goods_nomenclature.version_at(self.transaction)
        except TrackedModel.DoesNotExist:
            self.logger.warning(
                "Goods nomenclature %s no longer exists at transaction %s "
                "but indent %s is still referring to it.",
                indent.indented_goods_nomenclature,
                self.transaction,
                indent,
            )
            return

        commodity = Commodity(obj=good, indent_obj=indent)
        collection = get_chapter_collection(good)
        snapshot = collection.get_snapshot(self.transaction, good.valid_between.lower)

        parent = snapshot.get_parent(commodity)
        if not parent:
            return

        if not self.parent_spans_child(parent.indent_obj, indent):
            raise self.violation(indent)


@skip_when_deleted
@only_applicable_after(date(2010, 1, 1))
class NIG5(BusinessRule):
    """
    When creating a goods nomenclature code, an origin must exist.

    This rule is only applicable to update extractions.
    """

    def validate(self, good):
        """
        Almost all goods nomenclatures must have an origin, excluding two
        scenarios:

            1) They are a top level code (depth/indent of 1)
            2) They were made before 2010-01-01 (legacy data)

        Therefore check for these two conditions, and if neither are met ensure an origin exists.
        """
        # The proper method of checking for root codes is to examine the indents
        # of the code and see whether the code has any ancestors or not.
        # However, this is slow and troublesome, because in theory the indent
        # can change over time so it's not clear which indent we should be
        # examining if there are multiple (except root codes should only ever
        # have 1).
        #
        # So instead we just check whether the code is a chapter code i.e. it
        # ends with eight zeroes. All and only root codes should have this
        # property.

        from commodities.models.orm import GoodsNomenclatureOrigin

        if not (
            good.code.is_chapter
            or GoodsNomenclatureOrigin.objects.filter(
                new_goods_nomenclature__sid=good.sid,
            )
            .approved_up_to_transaction(good.transaction)
            .exists()
        ):
            raise self.violation(
                model=good,
                message="Non top-level goods must have an origin specified.",
            )


class NIG7(BusinessRule):
    """The origin must be applicable the day before the start date of the new
    code entered."""

    def validate(self, origin):
        """
        By default the upper bound is exclusive whilst the lower bound is
        inclusive.

        So we just need to make sure the bounds match.
        """

        origin_range = origin.derived_from_goods_nomenclature.valid_between
        starts_on = origin.new_goods_nomenclature.valid_between.lower
        day_before_start = starts_on - timedelta(days=1)

        if day_before_start not in origin_range:
            raise self.violation(
                model=origin,
                message=(
                    'The "derived from" code, if entered, must be a goods '
                    "nomenclature which exists and is applicable the day before the "
                    "start date of the new code entered. "
                    f"Origin {origin_range} is not applicable on {day_before_start}."
                ),
            )


@skip_when_deleted
class NIG10(BusinessRule):
    """The successor must be applicable the day after the end date of the old
    code."""

    def validate(self, successor):
        ends_on = successor.replaced_goods_nomenclature.valid_between.upper
        successor_range = successor.absorbed_into_goods_nomenclature.valid_between

        if ends_on is None:
            raise self.violation(
                model=successor,
                message=(
                    "A successor can only be added for goods nomenclature codes with a "
                    "closing date."
                ),
            )

        day_after_end = ends_on + timedelta(days=1)
        if day_after_end not in successor_range:
            raise self.violation(
                model=successor,
                message=(
                    'The "absorbed by" code, if entered, must be a goods nomenclature '
                    "which exists and is applicable the day after the closing date."
                    f"Successor {successor_range} is not applicable on {day_after_end}."
                ),
            )


class NIG11(ValidityStartDateRules):
    """
    At least one indent record is mandatory.

    The start date of the first indentation must be equal to the start date of
    the nomenclature. No two associated indentations may have the same start
    date. The start date must be less than or equal to the end date of the
    nomenclature.
    """

    model_name = "goods nomenclature"
    item_name = "indent"

    def get_objects(self, good):
        GoodsNomenclatureIndent = good.indents.model

        return GoodsNomenclatureIndent.objects.filter(
            indented_goods_nomenclature__sid=good.sid,
        ).approved_up_to_transaction(self.transaction)


class NIG12(DescriptionsRules):
    """
    At least one description is mandatory.

    The start date of the first description period must be equal to the start
    date of the nomenclature. No two associated description periods may have the
    same start date. The start date must be less than or equal to the end date
    of the nomenclature.
    """

    model_name = "goods nomenclature"


class NIG18(FootnoteApplicability):
    """Footnotes with a footnote type for which the application type = "CN
    footnotes" must be linked to CN lines (all codes up to 8 digits)."""

    applicable_field = "goods_nomenclature"


class NIG22(ValidityPeriodContained):
    """The period of the association with a footnote must be within the validity
    period of the nomenclature."""

    container_field_name = "goods_nomenclature"


class NIG23(ValidityPeriodContained):
    """The period of the association with a footnote must be within the validity
    period of the footnote."""

    container_field_name = "associated_footnote"


class NIG24(BusinessRule):
    """When the same footnote is associated more than once with the same
    nomenclature then there may be no overlap in their association periods."""

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
            .approved_up_to_transaction(association.transaction)
            .exclude(
                id=association.pk,
            )
        )

        if overlapping.exists():
            raise self.violation(association)


class NIG30(ValidityPeriodContained):
    """When a goods nomenclature is used in a goods measure then the validity
    period of the goods nomenclature must span the validity period of the goods
    measure."""

    contained_field_name = "measures"


class NIG31(NIG30):
    """When a goods nomenclature is used in an additional nomenclature measure
    then the validity period of the goods nomenclature must span the validity
    period of the additional nomenclature measure."""

    extra_filters = {
        "additional_code__isnull": False,
    }


class NIG34(PreventDeleteIfInUse):
    """A goods nomenclature cannot be deleted if it is used in a goods
    measure."""


@skip_when_not_deleted
class NIG35(BusinessRule):
    """A goods nomenclature cannot be deleted if it is used in an additional
    nomenclature measure."""

    # XXX this is redundant - NIG34 will be violated first

    def has_violation(self, good):
        return (
            good.measures.model.objects.filter(
                goods_nomenclature__sid=good.sid,
                additional_code__isnull=False,
            )
            .approved_up_to_transaction(
                self.transaction,
            )
            .exists()
        )

    def validate(self, good):
        if self.has_violation(good):
            raise self.violation(good)
