from contextlib import contextmanager
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from common.business_rules import BusinessRule
from common.business_rules import BusinessRuleChecker
from common.tests import factories

pytestmark = pytest.mark.django_db


class TestRule(BusinessRule):
    __test__ = False
    validate = MagicMock()


def test_business_rule_violation_message():
    model = MagicMock()
    violation = TestRule().violation(model)

    assert isinstance(violation, TestRule.Violation)
    assert violation.args == (None, model)
    assert violation.model == model

    setattr(TestRule.Violation, "__doc__", "A test message")
    violation = TestRule().violation(model)

    assert violation.args == ("A test message", model)

    violation = TestRule().violation(model, "A different message")

    assert violation.args == ("A different message", model)


@contextmanager
def add_business_rules(model, rules=[], indirect=False):
    with patch.object(
        type(model),
        f"{'indirect_' if indirect else ''}business_rules",
        new=rules,
    ):
        yield


def test_business_rules_validation():
    model = factories.TestModel1Factory()

    with add_business_rules(model, [TestRule]):
        BusinessRuleChecker([model]).validate()

    assert TestRule.validate.called_with(model)


def test_indirect_business_rule_validation():
    model = factories.TestModel3Factory()

    with add_business_rules(model, [TestRule]), add_business_rules(
        model.linked_model,
        [TestRule],
        indirect=True,
    ):
        BusinessRuleChecker([model.linked_model]).validate()

    assert TestRule.validate.called_with(model)
