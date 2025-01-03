from contextlib import contextmanager
from typing import Type
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from commodities.models.orm import GoodsNomenclatureDescription
from common.business_rules import BusinessRule
from common.business_rules import BusinessRuleViolation
from common.business_rules import NoBlankDescription
from common.business_rules import NoOverlapping
from common.business_rules import PreventDeleteIfInUse
from common.business_rules import UniqueIdentifyingFields
from common.business_rules import skip_when_deleted
from common.business_rules import skip_when_not_deleted
from common.models.mixins.description import DescriptionMixin
from common.tests import factories
from common.tests.util import raises_if
from common.validators import UpdateType

pytestmark = pytest.mark.django_db


class TestRule(BusinessRule):
    __test__ = False
    validate = MagicMock()


@pytest.mark.business_rules
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


@pytest.mark.business_rules
@contextmanager
def add_business_rules(model, rules=None, indirect=False):
    rules = rules or []
    with patch.object(
        type(model),
        f"{'indirect_' if indirect else ''}business_rules",
        new=rules,
    ):
        yield


@pytest.fixture(
    params=[
        UniqueIdentifyingFields,
        NoOverlapping,
    ],
)
def rule(request) -> Type[BusinessRule]:
    return request.param


@pytest.mark.business_rules
def test_rule_with_no_other_models(rule):
    model = factories.TestModel1Factory.create()
    rule(model.transaction).validate(model)


@pytest.mark.business_rules
def test_rule_with_no_overlaps(rule):
    model = factories.TestModel1Factory.create()
    other = factories.TestModel1Factory.create()
    rule(model.transaction).validate(model)
    rule(other.transaction).validate(other)


@pytest.mark.business_rules
def test_rule_with_versions(rule, workbasket):
    version1 = factories.TestModel1Factory.create()
    version2 = version1.new_version(workbasket)
    rule(version1.transaction).validate(version1)
    rule(version2.transaction).validate(version2)


@pytest.mark.business_rules
def test_unique_identifying_fields_with_overlaps():
    model = factories.TestModel1Factory.create()
    other = factories.TestModel1Factory.create(sid=model.sid)
    with pytest.raises(BusinessRuleViolation):
        UniqueIdentifyingFields(other.transaction).validate(model)
    with pytest.raises(BusinessRuleViolation):
        UniqueIdentifyingFields(other.transaction).validate(other)


@pytest.mark.business_rules
def test_unique_identifying_fields_with_custom_fields():
    model = factories.TestModel2Factory.create()
    UniqueIdentifyingFields(model.transaction).validate(model)

    other = factories.TestModel2Factory.create(custom_sid=model.custom_sid)
    with pytest.raises(BusinessRuleViolation):
        UniqueIdentifyingFields(other.transaction).validate(other)


@pytest.mark.business_rules
@pytest.mark.parametrize(
    ("description", "error_expected"),
    (
        ("Test description", False),
        ("", True),
        ("  ", True),
        ("\t", True),
        ("\n", True),
        (None, True),
    ),
)
def test_no_blank_descriptions(description, error_expected):
    description = factories.TestModelDescription1Factory(description=description)
    with raises_if(BusinessRuleViolation, error_expected):
        NoBlankDescription(description.transaction).validate(description)


@pytest.mark.business_rules
@pytest.mark.parametrize(
    ("description_model"),
    (DescriptionMixin.__subclasses__()),
    ids=(m.__name__ for m in DescriptionMixin.__subclasses__()),
)
def test_description_models_have_no_blanks_business_rule(description_model):
    """
    As the business rules are defined on the DescriptionMixin, it is easy to
    override them with a model-specific attribute that doesn't include
    NoBlankDescription.

    So this test acts as a check that all of the description models actually
    implement the business rule, either explicitly or implicitly.
    """
    if description_model == GoodsNomenclatureDescription:
        pytest.skip(
            "Blank descriptions are now allowed on GoodsNomenclatureDescription.",
        )
    assert NoBlankDescription in description_model.business_rules


class TestInUse(PreventDeleteIfInUse):
    __test__ = False


@pytest.mark.business_rules
def test_prevent_delete_if_in_use(approved_transaction):
    with approved_transaction:
        model = factories.TestModel3Factory.create()

    # skips because not a DELETE
    TestInUse(model.transaction).validate(model)

    workbasket = factories.WorkBasketFactory.create()
    model = model.new_version(workbasket, update_type=UpdateType.DELETE)
    model.in_use = MagicMock(return_value=True)

    with pytest.raises(TestInUse.Violation):
        TestInUse(model.transaction).validate(model)

    assert model.in_use.called


@pytest.mark.business_rules
@skip_when_deleted
class SkipWhenDeletedRule(BusinessRule):
    def validate():
        pass


@pytest.mark.business_rules
@pytest.mark.s
def test_skip_when_deleted(capfd):
    model = factories.TestModel1Factory.create(update_type=UpdateType.DELETE)
    SkipWhenDeletedRule(model.transaction).validate(model)

    assert "Skipping SkipWhenDeletedRule: update_type is 2" in capfd.readouterr().err


@pytest.mark.business_rules
@skip_when_not_deleted
class SkipWhenNotDeletedRule(BusinessRule):
    def validate():
        pass


@pytest.mark.business_rules
@pytest.mark.s
@pytest.mark.parametrize("update_type", [UpdateType.CREATE, UpdateType.UPDATE])
def test_skip_when_not_deleted(capfd, update_type):
    model = factories.TestModel1Factory.create(update_type=update_type)
    SkipWhenNotDeletedRule(model.transaction).validate(model)

    assert (
        f"Skipping SkipWhenNotDeletedRule: update_type is {update_type}"
        in capfd.readouterr().err
    )
