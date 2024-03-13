from datetime import date

import pytest

from common.business_rules import BusinessRuleViolation
from common.tests import factories
from common.tests.util import only_applicable_after
from common.util import TaricDateRange
from quotas import business_rules

pytestmark = pytest.mark.django_db


@only_applicable_after("2007-12-31")
def test_ON10(date_ranges):
    """
    When a quota order number is used in a measure then the validity period of
    the quota order number origin must span the validity period of the measure.

    This rule is only applicable for measures with start date after 31/12/2007.
    """

    measure = factories.MeasureWithQuotaFactory.create(
        order_number__origin__valid_between=date_ranges.normal,
        valid_between=date_ranges.overlap_normal,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ON10(measure.transaction).validate(
            measure.order_number.quotaordernumberorigin_set.first(),
        )


def test_ON10_multiple_active_origins():
    """Tests that it is possible to create multiple quota origins, as long as a
    measure with a quota is covered by at least one of these origins."""
    valid_between = TaricDateRange(date(2020, 1, 1), date(2020, 1, 31))
    measure = factories.MeasureWithQuotaFactory.create(
        order_number__origin__valid_between=valid_between,
        valid_between=valid_between,
    )
    later_origin = factories.QuotaOrderNumberOriginFactory.create(
        order_number=measure.order_number,
        valid_between=TaricDateRange(date(2021, 1, 1), date(2021, 1, 31)),
    )

    business_rules.ON10(later_origin.transaction).validate(later_origin)
    assert later_origin.transaction.workbasket.tracked_model_check_errors.count() == 0


def test_ON10_not_effective_valid_between():
    unapproved_transaction = factories.UnapprovedTransactionFactory.create()

    valid_between = TaricDateRange(date(2020, 1, 1), date(2022, 1, 1))

    measure = factories.MeasureWithQuotaFactory.create(
        order_number__origin__valid_between=TaricDateRange(
            date(2021, 1, 1),
            date(2021, 1, 31),
        ),
        valid_between=valid_between,
        transaction=unapproved_transaction,
    )

    origin = factories.QuotaOrderNumberOriginFactory.create(
        order_number=measure.order_number,
        valid_between=TaricDateRange(date(2021, 1, 1), date(2021, 1, 31)),
        transaction=unapproved_transaction,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ON10(origin.transaction).validate(origin)
        assert unapproved_transaction.workbasket.tracked_model_checks.count() > 0


def test_ON10_is_effective_valid_between():
    unapproved_transaction = factories.UnapprovedTransactionFactory.create()

    regulation = factories.RegulationFactory.create(
        effective_end_date=date(2021, 1, 31),
    )

    valid_between = TaricDateRange(date(2020, 1, 1), None)

    measure = factories.MeasureWithQuotaFactory.create(
        order_number__origin__valid_between=TaricDateRange(
            date(2020, 1, 1),
            date(2021, 1, 31),
        ),
        valid_between=valid_between,
        generating_regulation=regulation,
        transaction=unapproved_transaction,
    )

    origin = factories.QuotaOrderNumberOriginFactory.create(
        order_number=measure.order_number,
        valid_between=TaricDateRange(date(2020, 1, 1), date(2021, 1, 31)),
        transaction=unapproved_transaction,
    )

    business_rules.ON10(origin.transaction).validate(origin)

    assert unapproved_transaction.workbasket.tracked_model_check_errors.count() == 0
