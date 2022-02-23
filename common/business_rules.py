"""Base classes for business rules and violations."""
from __future__ import annotations

import logging
from datetime import date
from datetime import datetime
from functools import wraps
from typing import Any
from typing import Dict
from typing import Iterable
from typing import Iterator
from typing import Mapping
from typing import Optional
from typing import Type
from typing import Union

from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError
from django.db.models import QuerySet

from common.models.mixins.validity import ValidityMixin
from common.models.tracked_utils import get_relations
from common.models.trackedmodel import TrackedModel
from common.models.utils import override_current_transaction
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
        :param transaction Transaction: Get latest approved versions of linked
            models as of this transaction
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

    :param cutoff Union[date, datetime, str]: The date, datetime or isoformat
        date string of the time before which the rule should not apply
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
    """
    Rule enforcing validity period of a container object completely contains the
    validity period of one more contained objects.

    Checks that the following is true:

        for contained_object in contained_objects:
            container_object.valid_between contains
            contained_object.valid_between
    """

    container_field_name: Optional[str] = None
    """
    The name of the field on the passed model that gives the object who's
    validity range should be bigger or equal at both ends.
    
    This value can be unspecified, in which case the default is that the passed
    model is the container model.
    
    The container may be null because some business rules refer to optional
    links. E.g. between additional codes and measures: in many cases the measure
    just may not be using an addiitonal code, but this rule is run against every
    measure. The case where the container has been deleted but the contained
    object has not been deleted yet should be prevented by other business rules
    but is of course possible to represent in the data, so we ignore that case
    too.
    """

    contained_field_name: Optional[str] = None
    """
    The name of a field (or double-underscore-seperated path to a field) on the
    passed model that gives the object(s) who's validity range should be smaller
    or equal at both ends.
    
    This value can be unspecified, in which case the default is that the passed
    model is the contained model.
    
    The contained object may be null because subrecords are not routinely
    deleted when the parent record is deleted. For example, if a footnote is
    attached to a measure but the measure is deleted, the footnote association
    may not be routinely cleared up. 
    
    Note that this one reason is why it is important to make sure we are
    checking against the latest versions because the object will still be
    linking via FK to the contained object version it was first attached to. The
    other good reason is that if the dates on the container or contained objects
    are modified, this business rule needs to be considering them.
    """

    extra_filters: Dict[str, Any] = {}
    """Any extra filters that should be applied to filter the contained
    objects."""

    def violating_models(self, model: TrackedModel) -> QuerySet[ValidityMixin]:
        current = model.get_versions().current()

        # Resolve our way to the contained models. The output from `follow_path`
        # will be all the models that should be contained.
        contained = current
        if self.contained_field_name:
            contained = contained.follow_path(self.contained_field_name)

        # Get the latest version of the container model. If the container is not
        # present, then skip the rule.
        container = current
        if self.container_field_name:
            container = container.follow_path(self.container_field_name)
        if not container.exists():
            return contained.none()

        # Scope the contained models down to just the ones we are testing.
        # Violating models are ones that are not contained by the valid between
        # from the container model.
        valid_between = container.get().valid_between

        return (
            contained.with_validity_field()
            .filter(**self.extra_filters)
            .exclude(
                **{
                    f"{contained.model.validity_field_name}__contained_by": valid_between,
                },
            )
        )

    def validate(self, model):
        with override_current_transaction(self.transaction):
            if self.violating_models(model).exists():
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


@skip_when_deleted
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


class ExclusionMembership(BusinessRule):
    """The excluded geographical area must be a member of the geographical area
    group."""

    excluded_from: str
    """The object that the geographical area is excluded from."""

    def validate(self, exclusion):
        geo_group = getattr(exclusion, self.excluded_from).geographical_area
        Membership = geo_group._meta.get_field("members").related_model

        if (
            not Membership.objects.approved_up_to_transaction(self.transaction)
            .filter(
                geo_group__sid=geo_group.sid,
                member__sid=exclusion.excluded_geographical_area.sid,
            )
            .exists()
        ):
            raise self.violation(exclusion)


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
