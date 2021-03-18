"""Business rules for quotas."""
from datetime import date
from decimal import Decimal

from common.business_rules import BusinessRule
from common.business_rules import PreventDeleteIfInUse
from common.business_rules import UniqueIdentifyingFields
from common.business_rules import ValidityPeriodContained
from common.business_rules import only_applicable_after
from common.validators import UpdateType
from geo_areas.validators import AreaCode
from quotas.validators import AdministrationMechanism
from quotas.validators import SubQuotaType


class PreventDeletingLinkedQuotaDefinitions(BusinessRule):
    """A deleted Quota Definition must not be referred to by a non-deleted
    relation."""

    sid_prefix = "quota_definition__"

    def get_relation_model(self, quota_definition):
        raise NotImplementedError(
            f"get_relation_model must be implemented on {self.__class__.__name__}.",
        )

    def validate(self, quota_definition):
        related_model = self.get_relation_model(quota_definition)
        if quota_definition.update_type == UpdateType.DELETE:
            kwargs = {f"{self.sid_prefix}sid": quota_definition.sid}
            if related_model.objects.approved_up_to_transaction(
                transaction=quota_definition.transaction,
            ).filter(**kwargs):
                raise self.violation(quota_definition)


class ON1(UniqueIdentifyingFields):
    """Quota order number id + start date must be unique."""

    identifying_fields = ("order_number", "valid_between__lower")


class ON2(BusinessRule):
    """There may be no overlap in time of two quota order numbers with the same
    quota order number id."""

    def validate(self, order_number):
        if (
            type(order_number)
            .objects.approved_up_to_transaction(order_number.transaction)
            .filter(
                order_number=order_number.order_number,
                valid_between__overlap=order_number.valid_between,
            )
            .exclude(sid=order_number.sid)
            .exists()
        ):
            raise self.violation(order_number)


class ON5(BusinessRule):
    """There may be no overlap in time of two quota order number origins with
    the same quota order number SID and geographical area id."""

    def validate(self, origin):
        if (
            type(origin)
            .objects.approved_up_to_transaction(origin.transaction)
            .filter(
                order_number__sid=origin.order_number.sid,
                geographical_area__sid=origin.geographical_area.sid,
                valid_between__overlap=origin.valid_between,
            )
            .exclude(sid=origin.sid)
            .exists()
        ):
            raise self.violation(
                model=origin,
                message=(
                    "There may be no overlap in time of two quota order number "
                    "origins with the same quota order number SID and geographical "
                    "area id."
                ),
            )


@only_applicable_after("2006-12-31")
class ON6(ValidityPeriodContained):
    """The validity period of the geographical area must span the validity
    period of the quota order number origin."""

    container_field_name = "geographical_area"


class ON7(ValidityPeriodContained):
    """The validity period of the quota order number must span the validity
    period of the quota order number origin."""

    container_field_name = "order_number"


class ON8(ON7):
    """The validity period of the quota order number must span the validity
    period of the referencing quota definition."""


@only_applicable_after("2007-12-31")
class ON9(BusinessRule):
    """When a quota order number is used in a measure then the validity period
    of the quota order number must span the validity period of the measure."""

    def validate(self, order_number):
        if (
            order_number.measure_set.model.objects.filter(
                order_number__sid=order_number.sid,
            )
            .with_effective_valid_between()
            .exclude(
                db_effective_valid_between__contained_by=order_number.valid_between,
            )
            .exists()
        ):
            raise self.violation(order_number)


@only_applicable_after("2007-12-31")
class ON10(BusinessRule):
    """When a quota order number is used in a measure then the validity period
    of the quota order number origin must span the validity period of the
    measure."""

    def validate(self, origin):
        # XXX should this take a QuotaOrderNumber and check all related
        # QuotaOrderNumberOrigins?
        if (
            origin.order_number.measure_set.model.objects.filter(
                order_number__sid=origin.order_number.sid,
            )
            .with_effective_valid_between()
            .exclude(
                db_effective_valid_between__contained_by=origin.valid_between,
            )
            .exists()
        ):
            raise self.violation(origin)


@only_applicable_after("2007-12-31")
class ON11(PreventDeleteIfInUse):
    """The quota order number cannot be deleted if it is used in a measure."""


@only_applicable_after("2007-12-31")
class ON12(PreventDeleteIfInUse):
    """The quota order number origin cannot be deleted if it is used in a
    measure."""


class ON13(BusinessRule):
    """An exclusion can only be entered if the order number origin is a geographical
    area group (area code = 1).
    """

    def validate(self, exclusion):
        if exclusion.origin.geographical_area.area_code != AreaCode.GROUP:
            raise self.violation(exclusion)


class ON14(BusinessRule):
    """The excluded geographical area must be a member of the geographical area
    group."""

    def validate(self, exclusion):
        if not exclusion.excluded_geographical_area.groups.filter(
            member__sid=exclusion.excluded_geographical_area.sid,
            geo_group__sid=exclusion.origin.geographical_area.sid,
        ).exists():
            raise self.violation(exclusion)


class QD1(UniqueIdentifyingFields):
    """Quota order number id + start date must be unique."""

    identifying_fields = ("order_number__sid", "valid_between__lower")


class QD7(ValidityPeriodContained):
    """The validity period of the quota definition must be spanned by one of the
    validity periods of the referenced quota order number."""

    # "one of the validity periods" suggests an order number can have more than one
    # validity period, but this is not true. QD7 mirrors ON8, to check the same
    # constraint whether adding a quota definition or an order number.

    container_field_name = "order_number"


class QD8(ValidityPeriodContained):
    """The validity period of the monetary unit code must span the validity
    period of the quota definition."""

    container_field_name = "monetary_unit"


class QD10(ValidityPeriodContained):
    """The validity period measurement unit code must span the validity period
    of the quota definition."""

    container_field_name = "measurement_unit"


class QD11(ValidityPeriodContained):
    """The validity period of the measurement unit qualifier code must span the
    validity period of the quota definition."""

    container_field_name = "measurement_unit_qualifier"


class PreventQuotaDefinitionDeletion(BusinessRule):
    """
    A Quota Definition cannot be deleted once the start date is in the past.

    The Quota Definition may be end-dated instead.
    """

    def validate(self, quota_definition):
        if quota_definition.update_type == UpdateType.DELETE:
            if quota_definition.valid_between.lower >= date.today():
                raise self.violation(quota_definition)


class QuotaAssociationMustReferToANonDeletedSubQuota(
    PreventDeletingLinkedQuotaDefinitions,
):
    """A Quota Association must refer to a non-deleted sub quota."""

    sid_prefix = "sub_quota__"

    def get_relation_model(self, quota_definition):
        return quota_definition.sub_quota_associations.model


class QuotaSuspensionMustReferToANonDeletedQuotaDefinition(
    PreventDeletingLinkedQuotaDefinitions,
):
    """A Quota Suspension must refer to a non-deleted Quota Definition."""

    def get_relation_model(self, quota_definition):
        return quota_definition.quotasuspension_set.model


class QuotaBlockingPeriodMustReferToANonDeletedQuotaDefinition(
    PreventDeletingLinkedQuotaDefinitions,
):
    """A Quota Blocking Period must refer to a non-deleted Quota Definition."""

    def get_relation_model(self, quota_definition):
        return quota_definition.quotablocking_set.model


class QA1(UniqueIdentifyingFields):
    """The association between two quota definitions must be unique."""


class QA2(ValidityPeriodContained):
    """The sub-quota's validity period must be entirely enclosed within the
    validity period of the main quota."""

    container_field_name = "main_quota"
    contained_field_name = "sub_quota"


class QA3(BusinessRule):
    """
    When converted to the measurement unit of the main quota, the volume of a
    sub-quota must always be lower than or equal to the volume of the main
    quota.

    (The wording of this rule implies that quotas with different units can be
    linked together and there is no business rule that prevents this from
    happening. However, historically there have been no quotas where the units
    have been different and we should maintain this going forward as the system
    has no conversion ratios or other way of relating units to each other.)
    """

    def validate(self, association):
        main = association.main_quota
        sub = association.sub_quota
        if not (
            sub.measurement_unit == main.measurement_unit
            and sub.volume <= main.volume
            and sub.initial_volume <= main.initial_volume
        ):
            raise self.violation(association)


class QA4(BusinessRule):
    """
    Whenever a sub-quota receives a coefficient, this has to be a strictly
    positive decimal number.

    When it is not specified a value 1 is always assumed.
    """

    def validate(self, association):
        if not association.coefficient > 0:
            raise self.violation(association)


class QA5(BusinessRule):
    """
    Whenever a sub-quota is defined with the 'equivalent' type, it must have the
    same volume as the ones associated with the parent quota.

    Moreover it must be defined with a coefficient not equal to 1. A sub-quota
    defined with the 'normal' type must have a coefficient of 1.
    """

    def validate(self, association):
        if association.sub_quota_relation_type == SubQuotaType.EQUIVALENT:

            if association.coefficient == Decimal("1.00000"):
                raise self.violation(
                    model=association,
                    message=(
                        "A sub-quota defined with the 'equivalent' type must have a "
                        "coefficient not equal to 1"
                    ),
                )

            if (
                association.main_quota.sub_quotas.values("volume")
                .order_by("volume")
                .distinct("volume")
                .count()
                > 1
            ):
                raise self.violation(
                    model=association,
                    message=(
                        "Whenever a sub-quota is defined with the 'equivalent' type, it "
                        "must have the same volume as the ones associated with the "
                        "parent quota."
                    ),
                )

        elif (
            association.sub_quota_relation_type == SubQuotaType.NORMAL
            and association.coefficient != Decimal("1.00000")
        ):
            raise self.violation(
                model=association,
                message=(
                    "A sub-quota defined with the 'normal' type must have a coefficient "
                    "equal to 1"
                ),
            )


class QA6(BusinessRule):
    """Sub-quotas associated with the same main quota must have the same
    relation type."""

    def validate(self, association):
        if (
            association.main_quota.sub_quota_associations.values(
                "sub_quota_relation_type",
            )
            .order_by("sub_quota_relation_type")
            .distinct("sub_quota_relation_type")
            .count()
            > 1
        ):
            raise self.violation(association)


class BlockingOnlyOfFCFSQuotas(BusinessRule):
    """Blocking periods are only applicable to FCFS quotas."""

    def validate(self, blocking):
        if (
            blocking.quota_definition.order_number.mechanism
            != AdministrationMechanism.FCFS
        ):
            raise self.violation(blocking)


class QBP2(BusinessRule):
    """The start date of the quota blocking period must be later than or equal
    to the start date of the quota validity period."""

    def validate(self, blocking):
        if blocking.valid_between.lower < blocking.quota_definition.valid_between.lower:
            raise self.violation(blocking)


class SuspensionsOnlyToFCFSQuotas(BusinessRule):
    """Quota suspensions are only applicable to First Come First Served
    quotas."""

    def validate(self, suspension):
        if (
            suspension.quota_definition.order_number.mechanism
            != AdministrationMechanism.FCFS
        ):
            raise self.violation(suspension)


class QSP2(ValidityPeriodContained):
    """The validity period of the quota must span the quota suspension
    period."""

    container_field_name = "quota_definition"
