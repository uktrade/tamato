from functools import cached_property
from typing import Collection
from typing import Dict
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
        except BusinessRuleViolation as e:
            success, message = False, str(e)
        except Exception as e:
            success, message = (
                False,
                f"An internal error occurred when processing checks, please notify a "
                f"TAP developer of this issue : {str(e)}",
            )
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

    Attributes:
        checker_cache (dict): (class attribute)  Cache of Business checkers created by ``of()``.
    """

    rule: Type[BusinessRule]

    _checker_cache: Dict[str, BusinessRule] = {}

    @classmethod
    def of(cls: Type, rule_type: Type[BusinessRule]) -> Type:
        """
        Return a subclass of a Checker, e.g. BusinessRuleChecker,
        IndirectBusinessRuleChecker that runs the passed in business rule.

        Example, creating a BusinessRuleChecker for ME32:

        >>> BusinessRuleChecker.of(measures.business_rules.ME32)
        <class 'checks.checks.BusinessRuleCheckerOf[measures.business_rules.ME32]'>

        This API is usually called by .applicable_to, however this docstring should
        illustrate what it does.

        Checkers are created once and then cached in _checker_cache.

        As well as a small performance improvement, caching aids debugging by ensuring
        the same checker instance is returned if the same cls is passed to ``of``.
        """
        checker_name = f"{cls.__name__}Of[{rule_type.__module__}.{rule_type.__name__}]"

        # If the checker class was already created, return it.
        checker_class = cls._checker_cache.get(checker_name)
        if checker_class is not None:
            return checker_class

        # No existing checker was found, so create it:

        class BusinessRuleCheckerOf(cls):
            # Creating this class explicitly in code is more readable than using type(...)
            # Once created the name will be mangled to include the rule to be checked.

            f"""Apply the following checks as specified in {rule_type.__name__}"""
            rule = rule_type

            def __repr__(self):
                return f"<{checker_name}>"

        BusinessRuleCheckerOf.__name__ = checker_name

        cls._checker_cache[checker_name] = BusinessRuleCheckerOf
        return BusinessRuleCheckerOf

    @classmethod
    def checkers_for(cls: Type[Self], model: TrackedModel) -> Collection[Self]:
        """If the rule attribute on this BusinessRuleChecker matches any in the
        supplied TrackedModel instance's business_rules, return it in a list,
        otherwise there are no matches so return an empty list."""
        if cls.rule in model.business_rules:
            return [cls()]
        return []

    def run(self, model: TrackedModel) -> CheckResult:
        """
        :return CheckResult, a Tuple(rule_passed: str, violation_reason: Optional[str]).
        """
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

    This is a base class: subclasses for checking specific rules are created by
    calling ``of()``.
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
        """Return a set of IndirectBusinessRuleCheckers for every model found on
        rule.get_linked_models."""
        rules = set()
        transaction = get_current_transaction()
        if cls.rule in model.indirect_business_rules:
            for linked_model in cls.rule.get_linked_models(model, transaction):
                rules.add(cls(linked_model))
        return rules

    def run(self, model: TrackedModel) -> CheckResult:
        """
        Return the result of running super.run, passing self.linked_model, and.

        return it as a CheckResult - a Tuple(rule_passed: str, violation_reason: Optional[str])
        """
        result, message = super().run(self.linked_model)
        message = f"{self.linked_model}: " + message if message else None
        return result, message


def checker_types() -> Iterator[Type[Checker]]:
    """
    Return all registered Checker types.

    See ``checks.checks.BusinessRuleChecker.of``.
    """
    for rule in ALL_RULES:
        yield BusinessRuleChecker.of(rule)
        yield IndirectBusinessRuleChecker.of(rule)


def applicable_to(model: TrackedModel) -> Iterator[Checker]:
    """Return instances of any Checker classes applicable to the supplied
    TrackedModel instance."""
    for checker_type in checker_types():
        yield from checker_type.checkers_for(model)
