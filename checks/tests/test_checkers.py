import pytest

from checks.checks import BusinessRuleChecker
from checks.checks import LinkedModelsBusinessRuleChecker

# from checks.checks import checker_types  # TODO
from checks.models import TrackedModelCheck
from common.tests import factories
from common.tests.util import TestRule1
from common.tests.util import TestRule2
from common.tests.util import add_business_rules

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "applicable_rules, rule_filter, expected_rules",
    [
        ({TestRule1}, None, {TestRule1}),
        ({TestRule1, TestRule2}, None, {TestRule1, TestRule2}),
        ({TestRule1, TestRule2}, [TestRule1], {TestRule1}),
        ({TestRule1}, [TestRule2], set()),
        (set(), None, set()),
    ],
)
def test_business_rules_validation(applicable_rules, rule_filter, expected_rules):
    """Verify that ``BusinessRuleChecker.apply_rule`` calls ``validate`` on it's
    matching BusinessRule."""
    model = factories.TestModel1Factory.create()

    with add_business_rules(type(model), *applicable_rules):
        model_rules = BusinessRuleChecker.get_model_rules(model)
        assert isinstance(model_rules, dict)

        if not expected_rules:
            assert model_rules == {}
            return

        assert model_rules == {model: expected_rules}
        check = BusinessRuleChecker.apply_rule(TestRule1, model.transaction, model)

        assert TestRule1.validate.called_with(model)
        assert isinstance(check, TrackedModelCheck)


@pytest.mark.parametrize(
    "checker, expected_error_message_template",
    [
        (
            BusinessRuleChecker,
            "{model} does not have {rule} in its business_rules attribute.",
        ),
        (
            LinkedModelsBusinessRuleChecker,
            "{model} does not have {rule} in its indirect_business_rules attribute.",
        ),
    ],
)
def test_business_rules_validation_raises_exception_for_unknown_rule(
    checker,
    expected_error_message_template,
):
    """Verify that calling apply_rule with a different rule to that specified in
    a TrackedModels business_rules attribute raises a ValueError."""
    model = factories.TestModel1Factory.create()
    expected_error_message = expected_error_message_template.format(
        model=model,
        rule=TestRule2,
    )

    with add_business_rules(type(model), TestRule1), add_business_rules(
        factories.TestModelDescription1Factory._meta.model,
        TestRule1,
        indirect=True,
    ):
        model_rules = checker.get_model_rules(model)
        assert isinstance(model_rules, dict)

        with pytest.raises(ValueError, match=expected_error_message):
            # Calling checker.apply_rule with a rule that doesn't apply should raise an error.
            checker.apply_rule(TestRule2, model.transaction, model)


# def test_indirect_business_rule_validation():
#     model = factories.TestModel1Factory.create()
#     descs = set(
#         factories.TestModelDescription1Factory.create_batch(
#             size=4,
#             described_record=model,
#         ),
#     )
#     check = checks.tests.factories.TransactionCheckFactory(
#         transaction=model.transaction,
#     )
#
#     with add_business_rules(type(model), TestRule), add_business_rules(
#         factories.TestModelDescription1Factory._meta.model,
#         TestRule,
#         indirect=True,
#     ):
#         checker_type = LinkedModelsBusinessRuleChecker.of(TestRule)
#         checkers = checker_type.checkers_for(model)
#
#     # Assert every checker has a unique name.
#     assert len(checkers) == len(set(c.name for c in checkers))
#
#     for checker in checkers:
#         checker.apply(model, check)
#
#     for desc in descs:
#         assert TestRule.validate.called_with(desc)


@pytest.mark.parametrize(
    "applicable_rules, expected_rules",
    [
        ({TestRule1.__name__}, {TestRule1}),
        # ({TestRule.__name__, 'other'}, {TestRule}),
        # ({'other'}, set()),
        # (set(), set()),
    ],
)
def test_indirect_business_rules_validation(applicable_rules, expected_rules):
    """Verify that ``LinkedModelsBusinessRuleChecker.apply_rule`` calls
    ``validate`` on it's matching BusinessRule."""
    model = factories.TestModel1Factory.create()
    desc1, desc2 = factories.TestModelDescription1Factory.create_batch(
        size=2,
        described_record=model,
    )

    with add_business_rules(type(model), TestRule1), add_business_rules(
        factories.TestModelDescription1Factory._meta.model,
        TestRule1,
        indirect=True,
    ):

        desc1_model_rules = LinkedModelsBusinessRuleChecker.get_model_rules(desc1)
        desc2_model_rules = LinkedModelsBusinessRuleChecker.get_model_rules(desc2)

        assert desc1_model_rules == {model: {TestRule1}}
        assert desc1_model_rules == desc2_model_rules

        # check = LinkedModelsBusinessRuleChecker.apply_rule(TestRule1, desc.transaction, desc)
        LinkedModelsBusinessRuleChecker.apply_rule(TestRule1, model.transaction, model)
        # LinkedModelsBusinessRuleChecker.apply_rule(TestRule1, model.transaction, model)

        TestRule1.validate.assert_called_once_with(model)
