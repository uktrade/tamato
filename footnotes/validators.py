"""
Validators for footnotes
"""
import re

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db.models.functions import Lower


class FootnoteTypeIDValidator(RegexValidator):
    def __init__(self, *args, **kwargs):
        super().__init__(r"^([A-Z]{2} ?|[A-Z]{3})$")


class FootnoteIDValidator(RegexValidator):
    def __init__(self, *args, **kwargs):
        super().__init__(r"^([0-9]{3}|[0-9]{5})$")


def valid_footnote_description(footnote):
    """FO4"""

    if footnote.footnotedescription_set.count() == 0:
        raise ValidationError("At least one footnote description record is mandatory")

    first_description = footnote.footnotedescription_set.order_by(
        Lower("valid_between")
    ).first()
    desc_start = first_description.valid_between.lower
    fn_start = footnote.valid_between.lower
    if desc_start != fn_start:
        raise ValidationError(
            f"The start date of the first description period ({desc_start}) must be equal to the start date of the footnote ({fn_start})"
        )


def valid_footnote_description_period(footnote_description):
    """FO4"""

    if (
        footnote_description.valid_between.lower
        > footnote_description.described_footnote.valid_between.upper
    ):
        raise ValidationError(
            "The start date must be less than or equal to the end date of the footnote"
        )


def valid_footnote_period(footnote):
    """FO17"""
    if not (
        footnote.valid_between.lower in footnote.footnote_type.valid_between
        and footnote.valid_between.upper <= footnote.footnote_type.valid_between.upper
    ):
        raise ValidationError(
            f"The validity period of the footnote type ({footnote.footnote_type.valid_between}) must span the validity period of the footnote ({footnote.valid_between})."
        )


def unique_footnote_type(footnote_type):
    """FOT1
    The type of the footnote must be unique.
    """

    FootnoteType = footnote_type.__class__
    # TODO depends on TrackedModel and WorkBasket implementation
    # existing = FootnoteType.live_objects.filter(footnote_type_id=footnote_type.footnote_type_id)
    existing = FootnoteType.objects.filter(
        footnote_type_id=footnote_type.footnote_type_id
    )
    if footnote_type.id:
        existing = existing.exclude(id=footnote_type.id)
    if len(existing) > 0:
        raise ValidationError("The type of the footnote must be unique")
