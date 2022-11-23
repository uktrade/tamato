import pytest

from checks.tests import factories
from checks.tests.util import assert_current
from checks.tests.util import assert_fresh
from checks.tests.util import assert_requires_update
from common.models.transactions import Transaction
from common.tests import factories as common_factories

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("approved", "order", "head_order", "head_latest", "expect_current"),
    (
        (False, 1, 2, True, True),
        (False, 1, 2, False, False),
        (True, 1, 2, True, True),
        (True, 1, 2, False, True),
        (True, 2, 1, False, False),
    ),
    ids=(
        "check of draft transaction with equal head transaction",
        "check of draft transaction with greater head transaction",
        "check of approved transaction with equal transactions",
        "check of approved transaction with lesser approved check transaction",
        "check of approved transaction with greater approved check transaction",
    ),
)
def test_current_queryset_returns_correct_results(
    approved,
    order,
    head_order,
    head_latest,
    expect_current,
):
    check = factories.TransactionCheckFactory.create(
        transaction__approved=approved,
        transaction__draft=not approved,
        transaction__order=order,
        head_transaction__approved=True,
        head_transaction__order=head_order,
    )

    if head_latest:
        latest = check.head_transaction
    else:
        latest = common_factories.TransactionFactory.create(
            approved=True,
            order=head_order + 1,
        )
    assert Transaction.objects.all().approved.last() == latest

    assert_current(check, expect_current)


@pytest.mark.parametrize(
    ("models_added", "models_removed", "expect_stale"),
    (
        (False, False, False),
        (False, True, True),
        (True, False, True),
        (True, True, True),
    ),
    ids=(
        "check of unmodified transaction",
        "check of transaction with added models",
        "check of transaction with removed models",
        "check of transaction with added and removed models",
    ),
)
def test_fresh_and_stale_querysets_return_correct_results(
    models_added,
    models_removed,
    expect_stale,
):
    txn = common_factories.TransactionFactory.create(draft=True)
    first = common_factories.TestModel1Factory.create(transaction=txn)
    last = common_factories.TestModel1Factory.create(transaction=txn)
    check = factories.TransactionCheckFactory.create(
        transaction=txn,
        latest_tracked_model=last,
    )

    if models_removed:
        first.delete()
        assert check.transaction.tracked_models.count() != check.tracked_model_count
    if models_added:
        common_factories.TestModel1Factory.create(transaction=check.transaction)

    assert_fresh(check, not expect_stale)


def test_current_fresh_check_does_not_require_update():
    check = factories.TransactionCheckFactory.create()

    assert_current(check)
    assert_fresh(check)
    assert_requires_update(check, False)


def test_stale_check_does_require_update():
    stale_check = factories.StaleTransactionCheckFactory.create()

    assert_current(stale_check)
    assert_requires_update(stale_check, True)


def test_current_fresh_check_made_after_stale_check_does_not_require_update():
    stale_check = factories.StaleTransactionCheckFactory.create()
    fresh_check = factories.TransactionCheckFactory.create(
        transaction=stale_check.transaction,
    )

    assert_fresh(fresh_check)
    assert_current(fresh_check)
    assert_requires_update(fresh_check, False)


def test_current_fresh_check_made_on_transaction_after_stale_check_requires_update():
    stale_check = factories.StaleTransactionCheckFactory.create()
    after_check = factories.TransactionCheckFactory.create(
        transaction__partition=stale_check.transaction.partition,
        transaction__order=stale_check.transaction.order + 1,
        transaction__workbasket=stale_check.transaction.workbasket,
    )
    assert after_check.transaction.workbasket == stale_check.transaction.workbasket

    assert_fresh(after_check)
    assert_current(after_check)
    assert_requires_update(after_check, True)


def test_check_after_stale_check_in_other_workbasket_does_not_require_update():
    stale_check = factories.StaleTransactionCheckFactory.create()
    after_check = factories.TransactionCheckFactory.create(
        transaction__partition=stale_check.transaction.partition,
        transaction__order=stale_check.transaction.order + 1,
    )
    assert after_check.transaction.workbasket != stale_check.transaction.workbasket

    assert_fresh(after_check)
    assert_current(after_check)
    assert_requires_update(after_check, False)


def test_current_fresh_check_made_on_transaction_after_updated_stale_check_does_not_require_update():
    stale_check = factories.StaleTransactionCheckFactory.create()
    fresh_check = factories.TransactionCheckFactory.create(
        transaction=stale_check.transaction,
    )
    assert_requires_update(fresh_check, False)

    after_check = factories.TransactionCheckFactory.create(
        transaction__partition=stale_check.transaction.partition,
        transaction__order=stale_check.transaction.order + 1,
    )

    assert_requires_update(after_check, False)


def test_check_with_no_models_does_not_require_update():
    check = factories.TransactionCheckFactory.create(empty=True)

    assert_fresh(check)
    assert_current(check)
    assert_requires_update(check, False)
