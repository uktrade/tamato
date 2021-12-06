"""Base classes for business rules and violations."""
from __future__ import annotations

import logging
from datetime import date
from datetime import datetime
from functools import wraps
from typing import Iterable
from typing import Iterator
from typing import Mapping
from typing import Optional
from typing import Type
from typing import Union

from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError
from django.db.models import QuerySet

from common.models.tracked_utils import get_relations
from common.models.trackedmodel import TrackedModel
from common.util import get_field_tuple
from common.validators import UpdateType

log = logging.getLogger(__name__)


class BusinessRuleViolation(Exception):
    """Base class for business rule violations."""

    def default_message(self) -> Optional[str]:
        """
        Get the first paragraph of the class docstring (if it exists) to use as
        the error message.

        :return Optional[str]: The error message
        """

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
    """
    Metaclass for all BusinessRules.

    Adds a :exception:BusinessRuleViolation nested class, which can be accessed
    as ``BusinessRuleSubclass.Violation``, and sets the docstring (and hence the
    default error message) to the docstring of the new class.
    """

    Violation: Type[BusinessRuleViolation]

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

    def __init__(self, transaction=None):
        self.transaction = transaction

    @classmethod
    def get_linked_models(
        cls: Type[BusinessRule],
        model: TrackedModel,
        transaction,
    ) -> Iterator[TrackedModel]:
        """
        Returns latest approved model instances that have relations to the
        passed ``model`` and have this business rule listed in their
        ``business_rules`` attribute.

        :param model TrackedModel: Get models linked to this model instance
        :param transaction Transaction: Get latest approved versions of linked models as of this
        transaction
        :rtype Iterator[TrackedModel]: The linked models
        """
        for field, related_model in get_relations(type(model)).items():
            business_rules = getattr(related_model, "business_rules", [])
            if cls in business_rules:
                if field.one_to_many or field.many_to_many:
                    related_instances = getattr(model, field.get_accessor_name()).all()
                else:
                    related_instances = [getattr(model, field.name)]
                for instance in related_instances:
                    try:
                        yield instance.version_at(transaction)
                    except TrackedModel.DoesNotExist:
                        # `related_instances` will contain all instances, even
                        # deleted ones, and `version_at` will return
                        # `DoesNotExist` if the item has been deleted as of a
                        # certain transaction. That's ok, because we can just
                        # skip running business rules against deleted things.
                        continue

    def validate(self, *args):
        """
        Perform business rule validation.

        :raises NotImplementedError: Must be overridden by subclasses
        """
        raise NotImplementedError()

    def violation(
        self,
        model: Optional[TrackedModel] = None,
        message: Optional[str] = None,
    ) -> BusinessRuleViolation:
        """
        Create a violation exception object.

        :param model Optional[TrackedModel]: The model that violates this business rule
        :param message Optional[str]: A message explaining the violation
        :rtype BusinessRuleViolation: An exception indicating a business rule violation
        """

        return getattr(self.__class__, "Violation", BusinessRuleViolation)(
            model=model,
            message=message,
        )


class BusinessRuleChecker:
    """Runs all business rules governing a specified collection of model
    instances and collects all violations."""

    def __init__(self, models: Iterable[TrackedModel], transaction):
        self.models = models
        self.transaction = transaction

    def validate(self):
        """
        Run business rules against the specified models in the given
        transaction.

        :raises ValidationError: All rule violations are raised in a single
        ValidationError
        """
        violations = []

        for model in self.models:
            for rule in model.business_rules:
                try:
                    rule(self.transaction).validate(model)
                except BusinessRuleViolation as violation:
                    violations.append(violation)

            for rule in model.indirect_business_rules:
                rule_instance = rule(self.transaction)
                for linked_model in rule.get_linked_models(model, self.transaction):
                    try:
                        rule_instance.validate(linked_model)
                    except BusinessRuleViolation as violation:
                        violations.append(violation)

        if any(violations):
            raise ValidationError(violations)


def only_applicable_after(cutoff: Union[date, datetime, str]):
    """
    Decorate BusinessRules to make them only applicable after a given date.

    :param cutoff Union[date, datetime, str]: The date, datetime or isoformat date
    string of the time before which the rule should not apply
    """

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
            rule_should_apply = (
                hasattr(model, "valid_between") and model.valid_between.lower > cutoff
            ) or (hasattr(model, "validity_start") and model.validity_start > cutoff)

            if rule_should_apply:
                _original_validate(self, model)
            else:
                log.debug("Skipping %s: Start date before cutoff", cls.__name__)

        cls.validate = validate
        return cls

    return decorator


def skip_when_update_type(cls: Type[BusinessRule], update_types: Iterable[UpdateType]):
    """
    Skip business rule validation for given update types.

    :param cls Type[BusinessRule]: The BusinessRule to decorate
    :param update_types Iterable[int]: The UpdateTypes to skip
    """
    _original_validate = cls.validate

    @wraps(_original_validate)
    def validate(self, model):
        if model.update_type in update_types:
            log.debug("Skipping %s: update_type is %s", cls.__name__, model.update_type)
        else:
            _original_validate(self, model)

    cls.validate = validate
    return cls


def skip_when_deleted(cls: Type[BusinessRule]):
    """
    Skip business rule when the model is being deleted.

    :param cls Type[BusinessRule]: BusinessRule to decorate
    """
    return skip_when_update_type(cls, (UpdateType.DELETE,))


def skip_when_not_deleted(cls: Type[BusinessRule]):
    """
    Skip business rule when the model is not being deleted.

    :param cls Type[BusinessRule]: The BusinessRule to decorate
    """
    return skip_when_update_type(cls, (UpdateType.CREATE, UpdateType.UPDATE))


class UniqueIdentifyingFields(BusinessRule):
    """Rule enforcing identifying fields are unique."""

    identifying_fields: Optional[Iterable[str]] = None

    def validate(self, model):
        """
        Check no other model has the same identifying fields, except other
        versions of the same model.

        :param model TrackedModel: The model to compare with
        :raises self.violation: Rule violation
        """
        identifying_fields = self.identifying_fields or model.identifying_fields
        query = dict(get_field_tuple(model, field) for field in identifying_fields)

        if (
            type(model)
            .objects.filter(**query)
            .approved_up_to_transaction(self.transaction)
            .exclude(version_group=model.version_group)
            .exists()
        ):
            raise self.violation(model)


class NoOverlapping(BusinessRule):
    """Rule enforcing no overlapping validity periods of instances of a
    model."""

    identifying_fields: Optional[Iterable[str]] = None

    def validate(self, model):
        """
        Check other models with the same identifying fields do not have
        overlapping validity periods, except other versions of the same model.

        :param model TrackedModel: The model to compare with
        :raises self.violation: Rule violation
        """
        identifying_fields = self.identifying_fields or model.identifying_fields
        query = dict(get_field_tuple(model, field) for field in identifying_fields)
        query["valid_between__overlap"] = model.valid_between

        if (
            model.__class__.objects.filter(**query)
            .approved_up_to_transaction(self.transaction)
            .exclude(version_group=model.version_group)
            .exists()
        ):
            raise self.violation(model)


@skip_when_not_deleted
class PreventDeleteIfInUse(BusinessRule):
    """Rule preventing deleting an in-use model."""

    in_use_check: str = "in_use"
    via_relation: Optional[str] = None

    def has_violation(self, model) -> bool:
        """
        Return True if the given model instance is "in use" - determined by calling the
        method on the model instance named in ``self.in_use_check``.

        :param model TrackedModel: The model to check
        :rtype bool: True if the specified model's "in use" method returns True
        """
        names = [self.via_relation] if self.via_relation else []
        return getattr(model, self.in_use_check)(self.transaction, *names)

    def validate(self, model):
        """
        Check whether the specified model violates this business rule.

        :param model TrackedModel: The model to check
        :raises BusinessRuleViolation: Raised if the passed model violates this business rule.
        """
        if self.has_violation(model):
            raise self.violation(model)

        log.debug("Passed %s: Not in use", self.__class__.__name__)


class ValidityPeriodContained(BusinessRule):
    """Rule enforcing validity period of a contained object (found through the
    ``contained_field_name``) is contained by a container object's validity
    period (found through the ``container_field_name``)."""

    container_field_name: Optional[str] = None
    contained_field_name: Optional[str] = None

    def query_contains_validity(self, container, contained, model):
        """
        Raise a violation unless the contained model validity period falls
        entirely within the validity period of the container model.

        :param container TrackedModel: The model whose validity should contain that of
        the contained model
        :param contained TrackedModel: The model whose validity should be contained by
        that of the container model
        :param model TrackedModel: The model to associate with the violation
        :raises self.violation: A business violation exception
        """
        if (
            not type(container)
            .objects.filter(
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
        """
        Check that the specified model or related model named by
        ``contained_field_name`` has a validity period that is within the
        validity period of the related model named by ``container_field_name``.

        :param model TrackedModel: The model to check
        """
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
            .approved_up_to_transaction(self.transaction)
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


class ValidityStartDateRules(BusinessRule):
    """Repeated rule pattern for descriptions."""

    messages: Mapping[str, str] = {
        "at least one": "At least one {item} record is mandatory.",
        "first start date": "The start of the first {item} must be equal to the start date of the {model}.",
        "duplicate start dates": "Two {item}s may not have the same start date.",
        "start after end": "The start date of the {item} must be less than or equal to the end date of the {model}.",
    }
    model_name: str
    item_name: str

    def generate_violation(self, model, message_key: str):
        msg = self.messages[message_key].format(
            model=self.model_name,
            item=self.item_name,
        )

        return self.violation(model, msg)

    def get_objects(self, model) -> QuerySet:
        raise NotImplementedError("Subclass should implement get_objects")

    def validate(self, model):
        objects = self.get_objects(model).order_by("validity_start")

        if objects.count() < 1:
            raise self.generate_violation(model, "at least one")

        valid_froms = objects.values_list("validity_start", flat=True)

        if not any(
            filter(lambda x: x == model.valid_between.lower, valid_froms),
        ):
            raise self.generate_violation(model, "first start date")

        if len(set(valid_froms)) != len(valid_froms):
            raise self.generate_violation(model, "duplicate start dates")

        if not model.valid_between.upper_inf and any(
            filter(lambda x: x > model.valid_between.upper, valid_froms),
        ):
            raise self.generate_violation(model, "start after end")


class DescriptionsRules(ValidityStartDateRules):
    """Repeated rule pattern for descriptions."""

    item_name = "description"

    def get_objects(self, model):
        return model.get_descriptions(self.transaction)


class NoBlankDescription(BusinessRule):
    """Descriptions should not be blank."""

    def validate(self, model):
        if not model.description or not model.description.strip():
            raise self.violation(model)


class FootnoteApplicability(BusinessRule):
    """Check that a footnote type can be applied to a certain model, based on
    the set of :class:`~footnote.validators.ApplicationCode` that the model
    reports is valid for itself."""

    applicable_field: str
    """The field containing a model to check applicability for. It must have a
    property or attribute called :attr:`footnote_application_codes`."""

    footnote_type_field: str = "associated_footnote__footnote_type"
    """The field containing a footnote type to check for applicability."""

    def validate(self, model):
        applicable_model = get_field_tuple(model, self.applicable_field)[1]
        footnote_type = get_field_tuple(model, self.footnote_type_field)[1]

        if (
            footnote_type.application_code
            not in applicable_model.footnote_application_codes
        ):
            raise self.violation(model)


class UpdateValidity(BusinessRule):
    """
    The update type of this object must be valid.

    The first update must be of type Create. Subsequent updates must not be of
    type Create. After an update of type Delete, there must be no further
    updates. Only one version of the object may be updated in a single
    transaction.
    """

    def validate(self, model):
        existing_objects = (
            model.__class__.objects.filter(
                version_group=model.version_group,
            )
            .exclude(id=model.id)
            .versions_up_to(self.transaction)
        )

        if existing_objects.exists():
            if model.update_type == UpdateType.CREATE:
                raise self.violation(
                    model,
                    "Only the first object update can be of type Create.",
                )

            if any(
                version.update_type == UpdateType.DELETE for version in existing_objects
            ):
                raise self.violation(
                    model,
                    "An object must not be updated after an update version of Delete.",
                )

            if any(
                version.transaction == self.transaction for version in existing_objects
            ):
                raise self.violation(
                    model,
                    "Only one version of an object can be updated in a single transaction.",
                )

        else:
            if model.update_type != UpdateType.CREATE:
                raise self.violation(
                    model,
                    "The first update of an object must be of type Create.",
                )
