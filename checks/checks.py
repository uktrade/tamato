import abc
import logging
import typing
from collections import defaultdict
from typing import Optional
from typing import Set
from typing import Tuple

from checks.models import BusinessRuleModel
from checks.models import BusinessRuleResult
from checks.models import TrackedModelCheck
from common.business_rules import BusinessRule
from common.models import TrackedModel
from common.models import Transaction
from common.models.utils import get_current_transaction

logger = logging.getLogger(__name__)

CheckResult = Tuple[bool, Optional[str]]


class Checker(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def get_model_rule_mapping(
        cls: abc.abstractclassmethod,
        model: TrackedModel,
        rules: Optional[Set[str]] = None,
    ) -> typing.Dict[TrackedModel, Set[str]]:
        """Implementing classes should return a dict mapping classes to sets of
        business rules that apply to them."""
        return {}

    @classmethod
    def apply_rules(
        cls,
        rules: typing.Sequence[BusinessRule],
        transaction: Transaction,
        model: TrackedModel,
    ):
        """
        TODO - Get rules_to_run - set of rules that have not been run.
        """
        # model.content_hash().digest()

        # rule_models = {
        #     rule_model.name: rule_model for rule_model in type(model).get_business_rule_models()
        # }
        # TrackedModel check represents and ongoing check

        # To minimise the amount of queries, data is fetched up front and results are batched where possible.
        rule_models = [*BusinessRuleModel.from_rules(rules)]

        head_transaction = Transaction.objects.approved().last()
        check, created = TrackedModelCheck.objects.get_or_create(
            model=model,
            head_transaction=head_transaction,
            # content_hash=model.content_hash().digest(),
        )

        # TODO: Get exclude existing rules
        results = [
            rule_model.get_result(model.transaction, model)
            for rule_model in rule_models
        ]

        results = BusinessRuleResult.objects.bulk_create(results)

        check.results.add(*results)
        print(results)
        return check


class BusinessRuleChecker(Checker):
    """A``Checker`` that runs a ``BusinessRule`` against a model."""

    @classmethod
    def get_model_rule_mapping(
        cls,
        model: TrackedModel,
        rules: Optional[Set[str]] = None,
    ):
        """
        Return a dict mapping business rules to the passed in model.

        This returns a dict, with the passed in model used as a key (this allows LinkedModelsBusinessRuleChecker to map models other than the passed in model to rules.)

        :param model: TrackedModel instance
        :param rules: Optional list of rule names to filter by.
        :return: Dict with one entry for the passed in model the values are the rule instances to apply.
        """
        if rules is None:
            return {model: set(model.business_rules)}

        # User passed in a certain set of rule names to run, filter the business rules by these names
        filtered_rules = {
            rule for rule in model.business_rules if rule.__name__ in rules
        }
        return {model: filtered_rules}


class LinkedModelsBusinessRuleChecker(Checker):
    """A ``Checker`` that runs a ``BusinessRule`` against a model that is linked
    to the model being checked, and for which a change in the checked model
    could result in a business rule failure against the linked model."""

    @classmethod
    def get_model_rule_mapping(cls, model: TrackedModel, rules: Optional[Set] = None):
        """
        :param model: Initial TrackedModel instance
        :param rules: Optional list of rule names to filter by.
        :return: Dict mapping linked models with sets of the BusinessRules that apply to them.
        """
        tx = get_current_transaction()

        model_rules = defaultdict(set)

        for rule in [*model.indirect_business_rules]:
            for linked_model in rule.get_linked_models(model, tx):
                if rules is not None and rule.__name__ not in rules:
                    continue

                model_rules[linked_model].add(rule)

        # Downcast to a dict - this API (and unit testing) a little more sane.
        return {**model_rules}


# Checkers in priority list order, checkers for linked models come first.
ALL_CHECKERS = {
    "LinkedModelsBusinessRuleChecker": LinkedModelsBusinessRuleChecker,
    "BusinessRuleChecker": BusinessRuleChecker,
}
