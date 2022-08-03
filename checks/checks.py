import logging
from collections import defaultdict
from typing import Optional
from typing import Set
from typing import Tuple

from django.conf import settings

from checks.models import TrackedModelCheck
from common.business_rules import BusinessRule
from common.business_rules import BusinessRuleViolation
from common.models import TrackedModel
from common.models import Transaction
from common.models.utils import get_current_transaction
from common.models.utils import override_current_transaction

logger = logging.getLogger(__name__)

CheckResult = Tuple[bool, Optional[str]]


class Checker:
    @classmethod
    def run_rule(
        cls,
        rule: BusinessRule,
        transaction: Transaction,
        model: TrackedModel,
    ) -> CheckResult:
        """
        Run a single business rule on a single model.

        :return CheckResult, a Tuple(rule_passed: str, violation_reason: Optional[str]).
        """
        logger.debug(f"run_rule %s %s %s", model, rule, transaction.pk)
        try:
            rule(transaction).validate(model)
            logger.debug(f"%s [tx:%s] %s [passed]", model, rule, transaction.pk)
            return True, None
        except BusinessRuleViolation as violation:
            reason = violation.args[0]
            logger.debug(f"%s [tx:%s] %s [failed]", model, rule, transaction.pk, reason)
            return False, reason

    @classmethod
    def apply_rule(
        cls,
        rule: BusinessRule,
        transaction: Transaction,
        model: TrackedModel,
    ):
        """
        Applies the check to the model and records success.

        :return: TrackedModelCheck instance containing the result of the check.

        During debugging the developer can set settings.RAISE_BUSINESS_RULE_FAILURES
        to True to raise business rule violations as exceptions.
        """
        success, message = False, None
        try:
            with override_current_transaction(transaction):
                success, message = cls.run_rule(rule, transaction, model)
        except Exception as e:
            success, message = False, str(e)
            if settings.RAISE_BUSINESS_RULE_FAILURES:
                raise
        finally:
            check, created = TrackedModelCheck.objects.get_or_create(
                {
                    "successful": success,
                    "message": message,
                    "content_hash": model.content_hash().digest(),
                },
                model=model,
                check_name=rule.__name__,
            )
            if not created:
                check.successful = success
                check.message = message
                check.content_hash = model.content_hash().digest()
                check.save()
            return check

    @classmethod
    def apply_rule_cached(
        cls,
        rule: BusinessRule,
        transaction: Transaction,
        model: TrackedModel,
    ):
        """
        If a matching TrackedModelCheck instance exists, returns it, otherwise
        check rule, and return the result as a TrackedModelCheck instance.

        :return: TrackedModelCheck instance containing the result of the check.
        """
        try:
            check = TrackedModelCheck.objects.get(
                model=model,
                check_name=rule.__name__,
            )
        except TrackedModelCheck.DoesNotExist:
            logger.debug(
                "apply_rule_cached (no existing check) %s, %s apply rule",
                rule.__name__,
                transaction,
            )
            return cls.apply_rule(rule, transaction, model)

        # Re-run the rule if the check is not successful.
        check_hash = bytes(check.content_hash)
        model_hash = model.content_hash().digest()
        if check_hash == model_hash:
            logger.debug(
                "apply_rule_cached (matching content hash) %s,  tx: %s,  using cached result %s",
                rule.__name__,
                transaction.pk,
                check,
            )
            return check

        logger.debug(
            "apply_rule_cached (check.content_hash != model.content_hash())  %s != %s %s, %s apply rule",
            check_hash,
            model_hash,
            rule.__name__,
            transaction,
        )
        check.delete()
        return cls.apply_rule(rule, transaction, model)


class BusinessRuleChecker(Checker):
    """Apply BusinessRules specified in a TrackedModels business_rules
    attribute."""

    @classmethod
    def get_model_rules(cls, model: TrackedModel, rules: Optional[Set[str]] = None):
        """

        :param model: TrackedModel instance
        :param rules: Optional list of rule names to filter by.
        :return: Dict mapping models to a set of the BusinessRules that apply to them.
        """
        model_rules = defaultdict(set)

        for rule in model.business_rules:
            if rules is not None and rule.__name__ not in rules:
                continue

            model_rules[model].add(rule)

        return model_rules


class LinkedModelsBusinessRuleChecker(Checker):
    """Apply BusinessRules specified in a TrackedModels indirect_business_rules
    attribute to models returned by get_linked_models on those rules."""

    @classmethod
    def apply_rule(
        cls,
        rule: BusinessRule,
        transaction: Transaction,
        model: TrackedModel,
    ):
        """
        LinkedModelsBusinessRuleChecker assumes that the linked models are still
        the current.

        versions (TODO - ensure a business rule checks this),

        The transaction to check is set to that of the model, which enables
        """
        return super().apply_rule(rule, model.transaction, model)

    @classmethod
    def get_model_rules(cls, model: TrackedModel, rules: Optional[Set] = None):
        """
        :param model: TrackedModel instance
        :param rules: Optional list of rule names to filter by.
        :return: Dict mapping models to a set of the BusinessRules that apply to them.
        """
        tx = get_current_transaction()

        model_rules = defaultdict(set)

        for rule in [*model.indirect_business_rules]:
            for linked_model in rule.get_linked_models(model, tx):
                if rules is not None and rule.__name__ not in rules:
                    continue

                model_rules[linked_model].add(rule)

        return model_rules


# Checkers in priority list order, checkers for linked models come first.
ALL_CHECKERS = {
    "LinkedModelsBusinessRuleChecker": LinkedModelsBusinessRuleChecker,
    "BusinessRuleChecker": BusinessRuleChecker,
}
