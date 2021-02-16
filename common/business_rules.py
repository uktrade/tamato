"""Base classes for business rules and violations."""
import logging
from datetime import date
from datetime import datetime
from functools import wraps
from typing import Iterable
from typing import Mapping
from typing import Optional
from typing import Union

from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.db.models import QuerySet
from django.db.models.functions import Lower

from common.models.records import TrackedModel
from common.util import get_field_tuple
from common.validators import UpdateType

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class BusinessRuleViolation(ValidationError):
    """Base class for business rule violations."""


class BusinessRule:
    """Represents a TARIC business rule."""

    def validate(self, *args):
        """Perform business rule validation."""
        raise NotImplementedError()

    def violation(
        self,
        model: Optional[Union[TrackedModel, str]] = None,
        msg: Optional[str] = None,
    ) -> BusinessRuleViolation:
        """Create a violation exception object."""

        if msg is None:
            if isinstance(model, str):
                # handle msg string passed as only param
                msg = model
                model = None
            else:
                # use the docstring as the error message, up to the first blank line
                msg, *_ = self.__doc__.split("\n\n", 1)
                # replace multiple whitspace (including newlines) with single spaces
                msg = " ".join(msg.split())

        if model:
            msg = f"{model.__class__.__name__} {model.pk}: {msg}"

        return BusinessRuleViolation(msg)


def only_applicable_after(cutoff: Union[date, datetime, str]):

    if isinstance(cutoff, str):
        cutoff = date.fromisoformat(cutoff)

    if isinstance(cutoff, datetime):
        cutoff = cutoff.date()

    def decorator(cls):
        @wraps(cls)
        def decorated():
            instance = cls()
            validate = instance.validate

            @wraps(validate)
            def validate_if_applicable(model):
                if model.valid_between.lower > cutoff:
                    validate(model)
                else:
                    log.debug("Skipping %s: Start date before cutoff", cls.__name__)

            instance.validate = validate_if_applicable

            return instance

        return decorated

    return decorator


class UniqueIdentifyingFields(BusinessRule):
    """Rule enforcing identifying fields are unique."""

    identifying_fields = None

    def validate(self, model):
        identifying_fields = self.identifying_fields or model.identifying_fields
        query = dict(get_field_tuple(model, field) for field in identifying_fields)

        if (
            model.__class__.objects.filter(**query)
            .current_as_of(model.transaction)
            .exists()
        ):
            raise self.violation(model)


class NoOverlapping(BusinessRule):
    """Rule enforcing no overlapping validity periods of instances of a
    model."""

    identifying_fields: Optional[Iterable[str]] = None

    def validate(self, model):
        identifying_fields = self.identifying_fields or model.identifying_fields
        query = dict(get_field_tuple(model, field) for field in identifying_fields)
        query["valid_between__overlap"] = model.valid_between

        if (
            model.__class__.objects.filter(**query)
            .current_as_of(model.transaction)
            .exclude(id=model.id)
            .exists()
        ):
            raise self.violation(model)


class PreventDeleteIfInUse(BusinessRule):
    """Rule preventing deleting an in-use model."""

    in_use_check = "in_use"

    def validate(self, model):
        if model.update_type != UpdateType.DELETE:
            log.debug("Skipping %s: Not a delete", self.__class__.__name__)
            return

        check = getattr(model, self.in_use_check)
        if check():
            raise self.violation(model)

        log.debug("Passed %s: Not in use", self.__class__.__name__)


class ValidityPeriodContained(BusinessRule):
    """Rule enforcing validity period is contained by a dependency's validity
    period."""

    container_field_name: Optional[str] = None
    contained_field_name: Optional[str] = None

    def query_contains_validity(self, container, contained, model):
        if (
            not container.__class__.objects.filter(
                **container.get_identifying_fields(),
            )
            .current_as_of(model.transaction)
            .filter(
                valid_between__contains=contained.valid_between,
            )
            .exists()
        ):
            raise self.violation(model)

    def validate(self, model):
        _, container = get_field_tuple(model, self.container_field_name)
        contained = model
        if self.contained_field_name:
            _, contained = get_field_tuple(model, self.contained_field_name)

        if not container:
            # TODO should this raise an exception?
            log.warning(
                "Skipping %s: Container field %s not found.",
                self.__class__.__name__,
                self.container_field_name,
            )
            return

        self.query_contains_validity(container, contained, model)


class MustExist(BusinessRule):
    """Rule enforcing a referenced record exists."""

    # TODO does this need to verify that the referenced record's validity period is
    # current?

    reference_field_name: Optional[str] = None

    def validate(self, model):
        try:
            if getattr(model, self.reference_field_name) is None:
                log.debug(
                    "Skipping %s: No reference to %s",
                    self.__class__.__name__,
                    self.reference_field_name,
                )
                return
        except ObjectDoesNotExist:
            raise self.violation(model)


def find_duplicate_start_dates(queryset: QuerySet) -> QuerySet:
    return (
        queryset.annotate(
            start_date=Lower("valid_between"),
        )
        .values("start_date")
        .annotate(
            start_date_matches=Count("start_date"),
        )
        .filter(
            start_date_matches__gt=1,
        )
    )


class DescriptionsRules(BusinessRule):
    """Repeated rule pattern for descriptions."""

    messages: Mapping[str, str] = {
        "at least one": "At least one {item} record is mandatory.",
        "first start date": "The start of the first {item} must be equal to the start date of the {model}.",
        "duplicate start dates": "Two {item}s may not have the same start date.",
        "start after end": "The start date of the {item} must be less than or equal to the end date of the {model}.",
    }
    model_name: str
    item_name: str = "description"

    def generate_violation(self, model, message_key: str):
        msg = self.messages[message_key].format(
            model=self.model_name,
            item=self.item_name,
        )

        return self.violation(model, msg)

    def get_descriptions(self, model) -> QuerySet:
        return model.get_descriptions(workbasket=model.transaction.workbasket)

    def validate(self, model):
        descriptions = self.get_descriptions(model).order_by("valid_between")

        if descriptions.count() < 1:
            raise self.generate_violation(model, "at least one")

        if not descriptions.filter(
            valid_between__startswith=model.valid_between.lower,
        ).exists():
            raise self.generate_violation(model, "first start date")

        if find_duplicate_start_dates(descriptions).exists():
            raise self.generate_violation(model, "duplicate start dates")

        if descriptions.filter(valid_between__fully_gt=model.valid_between).exists():
            raise self.generate_violation(model, "start after end")
