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
