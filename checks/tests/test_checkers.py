from itertools import chain

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
    checkers = set(checker.rule for checker in checker_types())
    model_type = trackedmodel_factory._meta.model
    model_rules = set(
        chain(model_type.business_rules, model_type.indirect_business_rules),
    )
    assert checkers.intersection(model_rules) == model_rules


def test_business_rules_validation():
    model = factories.TestModel1Factory.create()
    check = checks.tests.factories.TransactionCheckFactory(
        transaction=model.transaction,
    )

    with add_business_rules(type(model), TestRule):
        checker_type = BusinessRuleChecker.of(TestRule)
        checkers = checker_type.checkers_for(model)

    for checker in checkers:
        checker.apply(model, check)
    assert TestRule.validate.called_with(model)


def test_indirect_business_rule_validation():
    model = factories.TestModel1Factory.create()
    descs = set(
        factories.TestModelDescription1Factory.create_batch(
            size=4,
            described_record=model,
        ),
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
        checkers = checker_type.checkers_for(model)

    # Assert every checker has a unique name.
    assert len(checkers) == len(set(c.name for c in checkers))

    for checker in checkers:
        checker.apply(model, check)

    for desc in descs:
        assert TestRule.validate.called_with(desc)
