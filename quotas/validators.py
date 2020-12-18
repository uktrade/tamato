"""Validators for quotas"""
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.core.validators import MinValueValidator
from django.core.validators import RegexValidator
from django.db import models


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


def validate_coefficient(value):
    if not value > 0:
        raise ValidationError(
            "Whenever a sub-quota receives a coefficient, this has to be a strictly positive decimal number."
        )
