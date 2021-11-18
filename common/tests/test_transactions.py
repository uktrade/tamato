"""Includes tests for select fuctionalities in TransactionQueryset."""
import pytest

from common.models.transactions import Transaction
from common.tests import factories
from workbaskets.models import get_partition_scheme

pytestmark = pytest.mark.django_db
partition_scheme = get_partition_scheme()


def test_unordered_tracked_models_are_linked_to_queryset():
    """Asserts that all models returned by unordered_tracked_models are in the
    workbasket."""
    transaction_this = factories.TransactionFactory()
    factories.MeasureFactory.create(
        transaction=transaction_this,
    )

    transaction_other = factories.TransactionFactory()
    factories.MeasureFactory.create(
        transaction=transaction_other,
    )

    qs = Transaction.objects.filter(id=transaction_this.id)
    unordered_tracked_models = qs.unordered_tracked_models()

    assert (
        unordered_tracked_models.filter(
            transaction=transaction_this,
        ).count()
        == unordered_tracked_models.count()
    )


def test_ordered_tracked_models_are_sorted_on_order():
    """Asserts that all models returned by ordered_tracked_models in the right
    order."""
    transaction_second = factories.TransactionFactory(order=2)
    factories.MeasureFactory.create(
        transaction=transaction_second,
    )

    transaction_first = factories.TransactionFactory(order=1)
    factories.MeasureFactory.create(
        transaction=transaction_first,
    )

    ids = (transaction_first.id, transaction_second.id)
    qs = Transaction.objects.filter(id__in=ids)
    ordered_tracked_models = qs.ordered_tracked_models().values_list(
        "transaction__order",
        flat=True,
    )

    assert sorted(ordered_tracked_models) == list(ordered_tracked_models)


def test_ordered_tracked_models_are_sorted_on_partition_and_order():
    """Asserts that all models returned by ordered_tracked_models in the right
    order."""
    transaction_first = factories.TransactionFactory(
        partition=partition_scheme.get_partition("PROPOSED"),
        order=2,
    )
    factories.MeasureFactory.create(
        transaction=transaction_first,
    )

    transaction_second = factories.TransactionFactory(
        partition=partition_scheme.get_approved_partition(),
        order=1,
    )
    factories.MeasureFactory.create(
        transaction=transaction_second,
    )

    ids = (transaction_first.id, transaction_second.id)
    qs = Transaction.objects.filter(id__in=ids)
    ordered_tracked_models = qs.ordered_tracked_models()

    assert (
        sorted(
            ordered_tracked_models,
            key=lambda x: (x.transaction.partition, x.transaction.order),
        )
        == list(ordered_tracked_models)
    )


def test_pre_ordering_of_querysets_with_negative_transaction_orders():
    """Asserts that querysets with negative tx orders assign negative orders to
    all transactions."""
    transaction_first = factories.TransactionFactory(order=-1)

    transaction_second = factories.TransactionFactory(order=1)

    ids = (transaction_first.id, transaction_second.id)
    qs = Transaction.objects.filter(id__in=ids)

    qs.preorder_negative_transactions()
    assert all(tx.order < 0 for tx in qs.all())


def test_ordering_of_querysets_with_negative_transaction_orders():
    """Asserts that querysets with negative or very large tx orders are ordered
    correctly."""
    transaction_first = factories.TransactionFactory(
        partition=partition_scheme.get_partition("PROPOSED"),
        order=-1,
    )

    transaction_second = factories.TransactionFactory(
        partition=partition_scheme.get_partition("PROPOSED"),
        order=99,
    )

    ids = (transaction_first.id, transaction_second.id)
    qs = Transaction.objects.filter(id__in=ids)

    qs.save_drafts(partition_scheme)
    assert sorted(tx.order for tx in qs.all()) == [0, 1]
