from datetime import date

import pytest

from common.business_rules import BusinessRuleViolation
from common.tests import factories
from common.util import TaricDateRange
from quotas import business_rules
from quotas.models import QuotaOrderNumber
from quotas.models import QuotaOrderNumberOrigin

pytestmark = pytest.mark.django_db


def test_ON4_pass(date_ranges, approved_transaction, unapproved_transaction):
    order_number = factories.QuotaOrderNumberFactory.create(
        valid_between=date_ranges.normal,
        transaction=unapproved_transaction,
    )

    assert business_rules.ON4(order_number.transaction).validate(order_number) is None


def test_ON4_fail(date_ranges, approved_transaction, unapproved_transaction):
    order_number = factories.QuotaOrderNumberFactory.create(
        valid_between=date_ranges.normal,
        transaction=approved_transaction,
        origin=None,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ON4(order_number.transaction).validate(order_number)


def test_ON4_pass_after_update(
    date_ranges,
    approved_transaction,
    unapproved_transaction,
):
    """The previous version of ON4 would fail at this point, since it would only
    look at origins for the current object (linked via tracked model id) but the
    updated version passes, since it looks at the version history for origins,
    not just the latest version of the model."""
    # Create the initial order number
    order_number = factories.QuotaOrderNumberFactory.create(
        valid_between=date_ranges.normal,
        transaction=approved_transaction,
    )

    assert QuotaOrderNumber.objects.all().count() == 1
    assert QuotaOrderNumberOrigin.objects.all().count() == 1

    # Update the order number
    workbasket = factories.WorkBasketFactory.create()
    transaction = workbasket.new_transaction()

    updated_order_number = order_number.new_version(
        workbasket=workbasket,
        transaction=transaction,
        valid_between=TaricDateRange(date(2022, 1, 1)),
    )

    assert business_rules.ON4(transaction).validate(updated_order_number) is None
