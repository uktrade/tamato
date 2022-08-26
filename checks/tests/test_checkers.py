import pytest

from checks.checks import BusinessRuleChecker
from checks.checks import LinkedModelsBusinessRuleChecker
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
def test_business_rules_validation(
    register_test_business_rules,
    applicable_rules,
    rule_filter,
    expected_rules,
):
    """Verify that ``BusinessRuleChecker.apply_rule`` calls ``validate`` on it's
    matching BusinessRule."""
    model = factories.TestModel1Factory.create()

    with add_business_rules(type(model), *applicable_rules):
        model_rules = BusinessRuleChecker.get_model_rule_mapping(model)
        assert isinstance(model_rules, dict)

        if not expected_rules:
            assert model_rules == {}
            return

        assert model_rules == {model: expected_rules}
        check = BusinessRuleChecker.apply_rules([TestRule1], model.transaction, model)

        assert TestRule1.validate.called_with(model)
        assert isinstance(check, TrackedModelCheck)


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

        desc1_model_rules = LinkedModelsBusinessRuleChecker.get_model_rule_mapping(
            desc1,
        )
        desc2_model_rules = LinkedModelsBusinessRuleChecker.get_model_rule_mapping(
            desc2,
        )

        assert desc1_model_rules == {model: {TestRule1}}
        assert desc1_model_rules == desc2_model_rules

        # check = LinkedModelsBusinessRuleChecker.apply_rule(TestRule1, desc.transaction, desc)
        LinkedModelsBusinessRuleChecker.apply_rules(
            [TestRule1],
            model.transaction,
            model,
        )
        # LinkedModelsBusinessRuleChecker.apply_rule(TestRule1, model.transaction, model)

        TestRule1.validate.assert_called_once_with(model)
