"""Base classes for business rules and violations."""
import logging
from datetime import date
from datetime import datetime
from functools import wraps
from typing import Iterable
from typing import Mapping
from typing import Optional
from typing import Type
from typing import Union

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import QuerySet

from common.models.records import TrackedModel
from common.util import get_field_tuple
from common.validators import UpdateType

log = logging.getLogger(__name__)


class BusinessRuleViolation(Exception):
    """Base class for business rule violations."""

    def default_message(self) -> Optional[str]:
        if self.__doc__:
            # use the docstring as the error message, up to the first blank line
            message, *_ = self.__doc__.split("\n\n", 1)

            # replace multiple whitespace (including newlines) with single spaces
            return " ".join(message.split())

        return None

    def __init__(self, model: TrackedModel, message: Optional[str] = None):
        self.model = model

        if not message:
            message = self.default_message()

        super().__init__(message, model)


class BusinessRuleBase(type):
    """Metaclass for all BusinessRules."""

    def __new__(cls, name, bases, attrs, **kwargs):
        parents = [parent for parent in bases if isinstance(parent, BusinessRuleBase)]

        # do not initialize base class
        if not parents:
            return super().__new__(cls, name, bases, attrs)

        new_class = super().__new__(cls, name, bases, attrs, **kwargs)

        # add BusinessRuleViolation subclass
        setattr(
            new_class,
            "Violation",
            type(
                "Violation",
                tuple(
                    parent.Violation
                    for parent in parents
                    if hasattr(parent, "Violation")
                )
                or (BusinessRuleViolation,),
                {
                    "__module__": attrs.get("__module__"),
                    "__qualname__": f"{new_class.__qualname__}.Violation",
                },
            ),
        )

        # set violation default message
        setattr(
            new_class.Violation,
            "__doc__",
            getattr(new_class, "__doc__", None),
        )

        return new_class


class BusinessRule(metaclass=BusinessRuleBase):
    """Represents a TARIC business rule."""

    Violation: Type[BusinessRuleViolation]

    def __init__(self, transaction):
        self.transaction = transaction

    @classmethod
    def get_linked_models(cls, model: TrackedModel) -> Iterable[TrackedModel]:
        for link in model._meta.related_objects:
            business_rules = getattr(link.related_model, "business_rules", [])
            if cls in business_rules:
                return getattr(
                    model,
                    link.related_name or f"{link.related_model._meta.model_name}_set",
                ).latest_approved()

        return []

    def validate(self, *args):
        """Perform business rule validation."""
        raise NotImplementedError()

    def violation(
        self,
        model: Optional[TrackedModel] = None,
        message: Optional[str] = None,
    ) -> BusinessRuleViolation:
        """Create a violation exception object."""

        return getattr(self.__class__, "Violation", BusinessRuleViolation)(
            model=model,
            message=message,
        )


class BusinessRuleChecker:
    def __init__(self, models: Iterable[TrackedModel], transaction):
        self.checks: set[tuple[type[BusinessRule], TrackedModel]] = set()

        self.transaction = transaction

        for model in models:
            for rule in model.business_rules:
                self.checks.add((rule, model))

            for rule in model.indirect_business_rules:
                for linked_model in rule.get_linked_models(model):
                    self.checks.add((rule, linked_model))

    def validate(self):
        for rule, model in self.checks:
            rule(self.transaction).validate(model)


def only_applicable_after(cutoff: Union[date, datetime, str]):

    if isinstance(cutoff, str):
        cutoff = date.fromisoformat(cutoff)

    if isinstance(cutoff, datetime):
        cutoff = cutoff.date()

    def decorator(cls):
        """
        Keep a copy of the wrapped model's original validation method and only
        call it if the model's validity start date is after the given date.

        The newly defined validate method is used to replace the model's own.
        ``_original_validate`` is a reference to the model's original validate
        method and remains in scope for the newly defined validate method.
        """
        _original_validate = cls.validate

        @wraps(_original_validate)
        def validate(self, model):
            if model.valid_between.lower > cutoff:
                _original_validate(self, model)
            else:
                log.debug("Skipping %s: Start date before cutoff", cls.__name__)

        cls.validate = validate
        return cls

    return decorator


class UniqueIdentifyingFields(BusinessRule):
    """Rule enforcing identifying fields are unique."""

    identifying_fields: Optional[Iterable[str]] = None

    def validate(self, model):
        identifying_fields = self.identifying_fields or model.identifying_fields
        query = dict(get_field_tuple(model, field) for field in identifying_fields)

        if (
            model.__class__.objects.filter(**query)
            .approved_up_to_transaction(self.transaction)
            .exclude(id=model.id)
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
            .approved_up_to_transaction(self.transaction)
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
    """Rule enforcing validity period of a contained object (found through the
    ``contained_field_name``) is contained by a container object's validity
    period (found through the ``container_field_name``)."""

    container_field_name: Optional[str] = None
    contained_field_name: Optional[str] = None

    def query_contains_validity(self, container, contained, model):
        if (
            not container.__class__.objects.filter(
                **container.get_identifying_fields(),
            )
            .approved_up_to_transaction(self.transaction)
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
            log.debug(
                "Skipping %s: Container field %s not found.",
                self.__class__.__name__,
                self.container_field_name,
            )
            return

        self.query_contains_validity(container, contained, model)


class ValidityPeriodContains(BusinessRule):
    """Rule enforcing validity period of this object contains a contained
    object's validity period (found through the ``contained_field_name``)."""

    contained_field_name: str

    def validate(self, model):
        contained_model = model
        relation_path = []
        for step in self.contained_field_name.split("__"):
            relation = {
                **contained_model._meta.fields_map,
                **contained_model._meta._forward_fields_map,
            }[step]
            contained_model = relation.related_model
            relation_path.append(relation.remote_field.name)

        if (
            contained_model.objects_with_validity_field()
            .filter(
                **{
                    f"{'__'.join(reversed(relation_path))}__{field}": value
                    for (field, value) in model.get_identifying_fields().items()
                }
            )
            .approved_up_to_transaction(model.transaction)
            .exclude(
                **{
                    f"{contained_model.validity_field_name}__contained_by": model.valid_between,
                },
            )
            .exists()
        ):
            raise self.violation(model)


class ValidityPeriodSpansContainer(BusinessRule):
    """Rule enforcing validity period of each contained value spans the validity
    period of the container."""

    contained_field_name: str

    def validate(self, model):
        container = model
        _, contained = get_field_tuple(model, self.contained_field_name)

        if (
            contained.approved_up_to_transaction(self.transaction)
            .exclude(
                valid_between__contains=container.valid_between,
            )
            .exists()
        ):
            raise self.violation(model)


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
        return model.get_descriptions(transaction=self.transaction)

    def validate(self, model):
        descriptions = self.get_descriptions(model).order_by("valid_between")

        if descriptions.count() < 1:
            raise self.generate_violation(model, "at least one")

        valid_betweens = descriptions.values_list("valid_between", flat=True)

        if not any(
            filter(lambda x: x.lower == model.valid_between.lower, valid_betweens),
        ):
            raise self.generate_violation(model, "first start date")

        if len({vb.lower for vb in valid_betweens}) != len(
            [vb.lower for vb in valid_betweens],
        ):
            raise self.generate_violation(model, "duplicate start dates")

        if not model.valid_between.upper_inf and any(
            filter(lambda x: x.lower > model.valid_between.upper, valid_betweens),
        ):
            raise self.generate_violation(model, "start after end")
