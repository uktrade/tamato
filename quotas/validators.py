"""Validators for quotas"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.core.validators import MinValueValidator
from django.core.validators import RegexValidator
from django.db import models

from common.util import validity_range_contains_range
from common.validators import UpdateType
from geo_areas.validators import AreaCode
from workbaskets.validators import WorkflowStatus


quota_order_number_validator = RegexValidator(r"^[0-9]{6}$")
monetary_unit_code_validator = RegexValidator(r"^[A-Z]{3}$")
measurement_unit_code_validator = RegexValidator(r"^[A-Z]{3}$")
measurement_unit_qualifier_code_validator = RegexValidator(r"^[A-Z]$")


def validate_max_precision(value):
    MinValueValidator(0)(value)
    MaxValueValidator(3)(value)


def validate_percentage(value):
    MinValueValidator(0)(value)
    MaxValueValidator(100)(value)


class AdministrationMechanism(models.IntegerChoices):
    FCFS = 0, "First come, first served"
    LICENSED = 1, "Licensed"


class QuotaCategory(models.IntegerChoices):
    WTO = 0, "WTO"
    AUTONOMOUS = 1, "Autonomous"
    PREFERENTIAL = 2, "Preferential"
    SAFEGUARD = 3, "Safeguard"


class SubQuotaType(models.TextChoices):
    EQUIVALENT = "EQ", "Equivalent to main quota"
    NORMAL = "NM", "Normal (restrictive to main quota)"


class BlockingPeriodType(models.IntegerChoices):
    LATE_PUBLICATION = 1, "Block the allocations for a quota due to a late publication"
    AFTER_VOLUME_INCREASE = (
        2,
        "Block the allocations for a quota after its reopening due to a volume increase",
    )
    AFTER_RETURN_REQUESTS = (
        3,
        "Block the allocations for a quota after its reopening due to the reception of quota return requests",
    )
    VALIDITY_PERIOD_CHANGE = (
        4,
        "Block the allocations for a quota due to the modification of the validity period after receiving quota return requests",
    )
    MSA_REQUEST = 5, "Block the allocations for a quota on request of a MSA"
    END_USER_DECISION = (
        6,
        "Block the allocations for a quota due to an end user decision",
    )
    EXCEPTIONAL_CONDITION = (
        7,
        "Block the allocations for a quota due to an exceptional condition",
    )
    AFTER_BALANCE_TRANSFER = (
        8,
        "Block the allocations for a quota after its reopening due to a balance transfer",
    )


class QuotaEventType(models.TextChoices):
    BALANCE = "00", "Quota balance event"
    UNBLOCKING = "05", "Quota unblocking event"
    CRITICAL = "10", "Quota critical state change event"
    EXHAUSTION = "15", "Quota exhaustion event"
    REOPENING = "20", "Quota reopening event"
    UNSUSPENSION = "25", "Quota unsuspension event"
    CLOSED = "30", "Quota closed and balance transferred event"


def validate_unique_id_and_start_date(order_number):
    """ON1"""

    order_numbers_with_id_and_start_date = (
        type(order_number)
        .objects.approved()
        .filter(
            sid=order_number.sid,
            valid_between__startswith=order_number.valid_between.lower,
        )
        .exclude(sid=order_number.sid)
    )
    if order_numbers_with_id_and_start_date.exists():
        raise ValidationError("Quota order number id + start date must be unique.")


def validate_no_overlapping_quota_order_numbers(order_number):
    """ON2"""

    order_numbers_with_overlapping_validity = (
        type(order_number)
        .objects.approved()
        .filter(
            order_number=order_number.order_number,
            valid_between__overlap=order_number.valid_between,
        )
        .exclude(sid=order_number.sid)
    )
    if order_numbers_with_overlapping_validity.exists():
        raise ValidationError(
            "There may be no overlap in time of two quota order numbers with the same "
            "quota order number id."
        )


def validate_no_overlapping_quota_order_number_origins(origin):
    """ON5"""

    origins_with_overlapping_validity_and_matching_geo_area_and_sid = (
        type(origin)
        .objects.approved()
        .filter(
            order_number__sid=origin.order_number.sid,
            geographical_area__sid=origin.geographical_area.sid,
            valid_between__overlap=origin.valid_between,
        )
        .exclude(sid=origin.sid)
    )
    if origins_with_overlapping_validity_and_matching_geo_area_and_sid.exists():
        raise ValidationError(
            "There may be no overlap in time of two quota order number origins with the "
            "same quota order number SID and geographical area id."
        )


def validate_geo_area_validity_spans_origin_validity(origin):
    """ON6"""

    if not validity_range_contains_range(
        origin.geographical_area.valid_between, origin.valid_between
    ):
        raise ValidationError(
            "The validity period of the geographical area must span the validity "
            "period of the quota order number origin."
        )


def validate_order_number_validity_spans_origin_validity(origin):
    """ON7"""

    if not validity_range_contains_range(
        origin.order_number.valid_between, origin.valid_between
    ):
        raise ValidationError(
            "The validity period of the quota order number must span the validity "
            "period of the quota order number origin."
        )


def validate_order_number_validity_spans_quota_definition_validity(definition):
    """ON7"""

    if not validity_range_contains_range(
        definition.order_number.valid_between, definition.valid_between
    ):
        raise ValidationError(
            "The validity period of the quota order number must span the validity "
            "period of the referencing quota definition."
        )


def validate_exclusion_only_from_group_origin(exclusion):
    """ON13"""

    if exclusion.origin.geographical_area.area_code != AreaCode.GROUP.value:
        raise ValidationError(
            "An exclusion can only be entered if the order number origin is a "
            "geographical area group (area code = 1)."
        )


def validate_excluded_geo_area_must_be_member_of_origin_group(exclusion):
    """ON14"""

    if not exclusion.excluded_geographical_area.groups.filter(
        geo_group=exclusion.origin.geographical_area
    ).exists():
        raise ValidationError(
            "The excluded geographical area must be a member of the geographical area group."
        )


def validate_unique_order_number_and_start_date(definition):
    """QD1"""

    definitions_with_order_number_and_start_date = (
        type(definition)
        .objects.approved()
        .filter(
            order_number=definition.order_number,
            valid_between__startswith=definition.valid_between.lower,
        )
        .exclude(sid=definition.sid)
    )
    if definitions_with_order_number_and_start_date.exists():
        raise ValidationError("Quota order number id + start date must be unique.")


def validate_unique_quota_association(association):
    """QA1"""

    associations = (
        type(association)
        .objects.approved()
        .filter(
            main_quota__sid=association.main_quota.sid,
            sub_quota__sid=association.sub_quota.sid,
        )
    )
    if association.update_type == UpdateType.CREATE and associations.exists():
        raise ValidationError(
            "The association between two quota definitions must be unique."
        )


def validate_sub_quota_validity_enclosed_by_main_quota_validity(association):
    """QA2"""

    if not validity_range_contains_range(
        association.main_quota.valid_between, association.sub_quota.valid_between,
    ):
        raise ValidationError(
            "The sub-quota's validity period must be entirely enclosed within the "
            "validity period of the main quota"
        )


def validate_coefficient(value):
    if not value > 0:
        raise ValidationError(
            "Whenever a sub-quota receives a coefficient, this has to be a strictly positive decimal number."
        )


def validate_equivalent_subquotas(association):
    """QA5"""

    if association.sub_quota_relation_type == SubQuotaType.EQUIVALENT:
        if not all(
            volume == association.sub_quota.volume
            for volume in association.main_quota.sub_quotas.values_list(
                "volume", flat=True
            )
        ):
            raise ValidationError(
                "Whenever a sub-quota is defined with the 'equivalent' type, it must have "
                "the same volume as the ones associated with the parent quota."
            )

        if association.coefficient == Decimal("1.00000"):
            raise ValidationError(
                "A sub-quota defined with the 'equivalent' type must have a "
                "coefficient not equal to 1"
            )


def validate_normal_subquotas(association):
    """Supplementary to QA5"""

    if association.sub_quota_relation_type == SubQuotaType.NORMAL:
        if association.coefficient != Decimal("1.00000"):
            raise ValidationError(
                "A sub-quota defined with the 'normal' type must have a coefficient "
                "equal to 1"
            )


def validate_sub_quotas_have_same_type(association):
    """QA6"""

    if not all(
        type == association.sub_quota_relation_type
        for type in association.main_quota.sub_quota_associations.values_list(
            "sub_quota_relation_type", flat=True
        )
    ):
        raise ValidationError(
            "Sub-quotas associated with the same main quota must have the same "
            "relation type"
        )


def validate_blocking_only_on_fcfs_quotas(blocking):
    if blocking.quota_definition.order_number.mechanism != AdministrationMechanism.FCFS:
        raise ValidationError("Blocking periods are only applicable to FCFS quotas.")


def validate_blocking_period_start_date(blocking):
    """QBP2"""

    if blocking.valid_between.lower < blocking.quota_definition.valid_between.lower:
        raise ValidationError(
            "The start date of the quota blocking period must be later than or equal "
            "to the start date of the quota validity period."
        )


def validate_suspension_only_on_fcfs_quotas(suspension):
    if (
        suspension.quota_definition.order_number.mechanism
        != AdministrationMechanism.FCFS
    ):
        raise ValidationError(
            "Quota suspensions are only applicable to First Come First Served quotas."
        )


def validate_suspension_period(suspension):
    """QSP2"""

    if not validity_range_contains_range(
        suspension.quota_definition.valid_between, suspension.valid_between
    ):
        raise ValidationError(
            "The validity period of the quota must span the quota suspension period."
        )
