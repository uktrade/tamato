from contextlib import contextmanager
from typing import Type
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from common.business_rules import BusinessRule
from common.business_rules import BusinessRuleChecker
from common.business_rules import BusinessRuleViolation
from common.business_rules import NoOverlapping
from common.business_rules import PreventDeleteIfInUse
from common.business_rules import UniqueIdentifyingFields
from common.business_rules import UpdateValidity
from common.tests import factories
from common.validators import UpdateType

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
    version2 = version1.new_version(workbasket)
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


class TestInUse(PreventDeleteIfInUse):
    __test__ = False


def test_prevent_delete_if_in_use(approved_transaction):
    with approved_transaction:
        model = factories.TestModel3Factory.create()

    with add_business_rules(model, [TestInUse]):

        # skips because not a DELETE
        BusinessRuleChecker([model], model.transaction).validate()

        workbasket = factories.WorkBasketFactory.create()
        model = model.new_version(workbasket, update_type=UpdateType.DELETE)
        model.in_use = MagicMock(return_value=True)

        with pytest.raises(BusinessRuleViolation):
            BusinessRuleChecker([model], model.transaction).validate()

    assert model.in_use.called


def test_UpdateValidity_first_update_must_be_Create():
    """The first update to an object must be of type Create."""
    version = factories.TestModel1Factory.create(update_type=UpdateType.DELETE)

    with pytest.raises(BusinessRuleViolation):
        UpdateValidity(version.transaction).validate(version)


def test_UpdateValidity_later_updates_must_not_be_Create():
    """Updates to an object after the first update must not be of type
    Create."""
    first_version = factories.TestModel1Factory.create()
    second_version = factories.TestModel1Factory.create(
        update_type=UpdateType.CREATE,
        version_group=first_version.version_group,
    )

    with pytest.raises(BusinessRuleViolation):
        UpdateValidity(second_version.transaction).validate(
            second_version,
        )


def test_UpdateValidity_must_not_update_after_Delete():
    """There must not be updates to an object version group after an update of
    type Delete."""
    first_version = factories.TestModel1Factory.create(
        update_type=UpdateType.DELETE,
    )
    second_version = factories.TestModel1Factory.create(
        update_type=UpdateType.UPDATE,
        version_group=first_version.version_group,
    )

    with pytest.raises(BusinessRuleViolation):
        UpdateValidity(second_version.transaction).validate(
            second_version,
        )


def test_UpdateValidity_only_one_version_per_transaction():
    """The transaction must contain no more than one update to each Certificate
    version group."""
    first_version = factories.TestModel1Factory.create()
    second_version = factories.TestModel1Factory.create(
        update_type=UpdateType.UPDATE,
        version_group=first_version.version_group,
        transaction=first_version.transaction,
    )

    with pytest.raises(BusinessRuleViolation):
        UpdateValidity(second_version.transaction).validate(
            second_version,
        )
