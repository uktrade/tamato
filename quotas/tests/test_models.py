import pytest

from common.tests import factories

pytestmark = pytest.mark.django_db


def test_quota_order_number_in_use(in_use_check_respects_deletes):
    assert in_use_check_respects_deletes(
        factories.QuotaOrderNumberFactory,
        "in_use",
        factories.MeasureFactory,
        "order_number",
    )


def test_quota_order_number_origin_in_use(in_use_check_respects_deletes):
    assert in_use_check_respects_deletes(
        factories.QuotaOrderNumberOriginFactory,
        "in_use",
        factories.MeasureFactory,
        "order_number",
        through="order_number",
    )


@pytest.mark.parametrize(
    "factory",
    [
        factories.QuotaOrderNumberFactory,
        factories.QuotaOrderNumberOriginFactory,
        factories.QuotaOrderNumberOriginExclusionFactory,
        factories.QuotaDefinitionFactory,
        factories.QuotaAssociationFactory,
        factories.QuotaSuspensionFactory,
        factories.QuotaBlockingFactory,
        factories.QuotaEventFactory,
    ],
)
def test_quota_update_types(
    factory,
    check_update_validation,
):
    assert check_update_validation(
        factory,
    )
