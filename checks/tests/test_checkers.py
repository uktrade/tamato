from itertools import chain
from unittest.mock import call

import pytest

import checks.tests.factories
from checks.checks import BusinessRuleChecker
from checks.checks import IndirectBusinessRuleChecker
from checks.checks import checker_types
from common.tests import factories
from common.tests.util import TestRule
from common.tests.util import add_business_rules

pytestmark = pytest.mark.django_db


def test_all_business_rules_have_a_checker(trackedmodel_factory):
    """Verify that each BusinessRule has a corresponding Checker."""
    checkers = set(checker.rule for checker in checker_types())
    model_type = trackedmodel_factory._meta.model
    model_rules = set(
        chain(model_type.business_rules, model_type.indirect_business_rules),
    )
    assert checkers.intersection(model_rules) == model_rules


def test_business_rules_validation():
    """Verify that ``Checker.apply`` calls ``validate`` on it's matching
    BusinessRule."""
    model = factories.TestModel1Factory.create()
    check = checks.tests.factories.TransactionCheckFactory(
        transaction=model.transaction,
    )

    with add_business_rules(type(model), TestRule):
        checker_type = BusinessRuleChecker.of(TestRule)

        # Verify the cache returns the same object if .of is called a second time.
        assert checker_type is BusinessRuleChecker.of(TestRule)

        checkers = checker_type.checkers_for(model)

    assert len(checkers)

    for checker in checkers:
        checker.apply(model, check)

    TestRule.validate.assert_called_once_with(model)


def test_indirect_business_rule_validation():
    model = factories.TestModel1Factory.create()
    desc1, desc2 = factories.TestModelDescription1Factory.create_batch(
        size=2,
        described_record=model,
    )
    check = checks.tests.factories.TransactionCheckFactory(
        transaction=model.transaction,
    )

    with add_business_rules(type(model), TestRule), add_business_rules(
        factories.TestModelDescription1Factory._meta.model,
        TestRule,
        indirect=True,
    ):
        checker_type = IndirectBusinessRuleChecker.of(TestRule)

        # Verify the cache returns the same object if .of is called a second time.
        assert checker_type is IndirectBusinessRuleChecker.of(TestRule)

        desc1_checkers = checker_type.checkers_for(desc1)
        desc2_checkers = checker_type.checkers_for(desc2)

        assert {type(checker) for checker in desc1_checkers} == {checker_type}
        assert {type(checker) for checker in desc2_checkers} == {checker_type}

        # Verify that applying the description checker calls validate on the
        # business rule TestRule with model
        for desc_checker in desc1_checkers | desc2_checkers:
            desc_checker.apply(model, check)

        TestRule.validate.assert_has_calls(
            [
                call(model),
                call(model),
            ],
        )
