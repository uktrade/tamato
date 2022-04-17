from functools import cached_property
from typing import Collection
from typing import Iterator
from typing import Optional
from typing import Tuple
from typing import Type
from typing import TypeVar

from checks.models import TrackedModelCheck
from checks.models import TransactionCheck
from common.business_rules import ALL_RULES
from common.business_rules import BusinessRule
from common.business_rules import BusinessRuleViolation
from common.models.trackedmodel import TrackedModel
from common.models.utils import get_current_transaction
from common.models.utils import override_current_transaction

CheckResult = Tuple[bool, Optional[str]]


Self = TypeVar("Self")


class Checker:
    """
    A ``Checker`` is an object that knows how to perform a certain kind of check
    against a model.

    Checkers can be applied against a model. The logic of the checker will be
    run and the result recorded as a ``TrackedModelCheck``.
    """

    @cached_property
    def name(self) -> str:
        """
        The name string that on a per-model basis uniquely identifies the
        checker.

        The name should be deterministic (i.e. not rely on the current
        environment, memory locations or random data) so that the system can
        record the name in the database and later use it to work out whether
        this check has been run. The name doesn't need to include any details
        about the model.

        By default this is the name of the class, but it can include any other
        non-model data that is unique to the checker. For a more complex
        example, see ``IndirectBusinessRuleChecker.name``.
        """
        return type(self).__name__

    @classmethod
    def checkers_for(cls: Type[Self], model: TrackedModel) -> Collection[Self]:
        """
        Returns instances of this ``Checker`` that should apply to the model.

        What checks apply to a model is sometimes data-dependent, so it is the
        responsibility of the ``Checker`` class to tell the system what
        instances of itself it would expect to run against the model. For an
        example, see ``IndirectBusinessRuleChecker.checkers_for``.
        """
        raise NotImplementedError()

    def run(self, model: TrackedModel) -> CheckResult:
        """Runs Checker-dependent logic and returns an indication of success."""
        raise NotImplementedError()

    def apply(self, model: TrackedModel, context: TransactionCheck):
        """Applies the check to the model and records success."""

        success, message = False, None
        try:
            with override_current_transaction(context.transaction):
                success, message = self.run(model)
        except Exception as e:
            success, message = False, str(e)
        finally:
            return TrackedModelCheck.objects.create(
                model=model,
                transaction_check=context,
                check_name=self.name,
                successful=success,
                message=message,
            )


class BusinessRuleChecker(Checker):
    """
    A ``Checker`` that runs a ``BusinessRule`` against a model.

    This class is expected to be sub-typed for a specific rule by a call to
    ``of()``.
    """

    rule: Type[BusinessRule]

    @classmethod
    def of(cls: Type, rule_type: Type[BusinessRule]) -> Type:
        """Returns a new checker class that can run the supplied rule."""

        class RuleChecker(cls):
            rule = rule_type

        RuleChecker.__name__ = (
            f"{cls.__name__}[{rule_type.__module__}.{rule_type.__name__}]"
        )
        return RuleChecker

    @classmethod
    def checkers_for(cls: Type[Self], model: TrackedModel) -> Collection[Self]:
        if cls.rule in model.business_rules:
            return [cls()]
        else:
            return []

    def run(self, model: TrackedModel) -> CheckResult:
        transaction = get_current_transaction()
        try:
            self.rule(transaction).validate(model)
            return True, None
        except BusinessRuleViolation as violation:
            return False, violation.args[0]


class IndirectBusinessRuleChecker(BusinessRuleChecker):
    """
    A ``Checker`` that runs a ``BusinessRule`` against a model that is linked to
    the model being checked, and for which a change in the checked model could
    result in a business rule failure against the linked model.

    This class is expected to be sub-typed for a specific rule by a call to
    ``of()``.
    """

    rule: Type[BusinessRule]
    linked_model: TrackedModel

    def __init__(self, linked_model: TrackedModel) -> None:
        self.linked_model = linked_model
        super().__init__()

    @cached_property
    def name(self) -> str:
        # Include the identity of the linked model in the checker name, so that
        # each linked model needs to be checked for all checks to be complete.
        return f"{super().name}[{self.linked_model.pk}]"

    @classmethod
    def checkers_for(cls: Type[Self], model: TrackedModel) -> Collection[Self]:
        rules = set()
        transaction = get_current_transaction()
        if cls.rule in model.indirect_business_rules:
            for linked_model in cls.rule.get_linked_models(model, transaction):
                rules.add(cls(linked_model))
        return rules

    def run(self, model: TrackedModel) -> CheckResult:
        result, message = super().run(self.linked_model)
        message = f"{self.linked_model}: " + message if message else None
        return result, message


def checker_types() -> Iterator[Type[Checker]]:
    """Returns all of the registered Checker types."""
    for rule in ALL_RULES:
        yield BusinessRuleChecker.of(rule)
        yield IndirectBusinessRuleChecker.of(rule)


def applicable_to(model: TrackedModel) -> Iterator[Checker]:
    """Returns all of the Checker instances that should be applicable to the
    passed model, with the names that should be recorded against them."""
    for checker_type in checker_types():
        yield from checker_type.checkers_for(model)
