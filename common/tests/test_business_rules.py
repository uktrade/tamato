from contextlib import contextmanager
from typing import Type
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from common.business_rules import BusinessRule
from common.business_rules import BusinessRuleChecker
from common.business_rules import BusinessRuleViolation
from common.business_rules import NoOverlapping
from common.business_rules import UniqueIdentifyingFields
from common.tests import factories

pytestmark = pytest.mark.django_db


class TestRule(BusinessRule):
    __test__ = False
    validate = MagicMock()


def test_business_rule_violation_message():
    model = MagicMock()
    violation = TestRule(model.transaction).violation(model)

    assert isinstance(violation, TestRule.Violation)
    assert violation.args == (None, model)
    assert violation.model == model

    setattr(TestRule.Violation, "__doc__", "A test message")
    violation = TestRule(model.transaction).violation(model)

    assert violation.args == ("A test message", model)

    violation = TestRule(model.transaction).violation(model, "A different message")

    assert violation.args == ("A different message", model)


@contextmanager
def add_business_rules(model, rules=None, indirect=False):
    rules = rules or []
    with patch.object(
        type(model),
        f"{'indirect_' if indirect else ''}business_rules",
        new=rules,
    ):
        yield


def test_business_rules_validation():
    model = factories.TestModel1Factory.create()

    with add_business_rules(model, [TestRule]):
        BusinessRuleChecker([model], model.transaction).validate()

    assert TestRule.validate.called_with(model)


def test_indirect_business_rule_validation():
    model = factories.TestModel3Factory.create()

    with add_business_rules(model, [TestRule]), add_business_rules(
        model.linked_model,
        [TestRule],
        indirect=True,
    ):
        BusinessRuleChecker([model.linked_model], model.transaction).validate()

    assert TestRule.validate.called_with(model)


@pytest.fixture(
    params=[
        UniqueIdentifyingFields,
        NoOverlapping,
    ],
)
def rule(request) -> Type[BusinessRule]:
    return request.param


def test_rule_with_no_other_models(rule):
    model = factories.TestModel1Factory.create()
    rule(model.transaction).validate(model)


def test_rule_with_no_overlaps(rule):
    model = factories.TestModel1Factory.create()
    other = factories.TestModel1Factory.create()
    rule(model.transaction).validate(model)
    rule(other.transaction).validate(other)


def test_rule_with_versions(rule, workbasket):
    version1 = factories.TestModel1Factory.create()
    version2 = version1.new_draft(workbasket)
    rule(version1.transaction).validate(version1)
    rule(version2.transaction).validate(version2)


def test_unique_identifying_fields_with_overlaps():
    model = factories.TestModel1Factory.create()
    other = factories.TestModel1Factory.create(sid=model.sid)
    with pytest.raises(BusinessRuleViolation):
        UniqueIdentifyingFields(other.transaction).validate(model)
    with pytest.raises(BusinessRuleViolation):
        UniqueIdentifyingFields(other.transaction).validate(other)


def test_unique_identifying_fields_with_custom_fields():
    model = factories.TestModel2Factory.create()
    UniqueIdentifyingFields(model.transaction).validate(model)

    other = factories.TestModel2Factory.create(custom_sid=model.custom_sid)
    with pytest.raises(BusinessRuleViolation):
        UniqueIdentifyingFields(other.transaction).validate(other)
