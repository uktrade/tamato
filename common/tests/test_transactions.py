"""Includes tests for select fuctionalities in TransactionQueryset."""
import pytest

from common.models.transactions import Transaction
from common.models.transactions import TransactionPartition
from common.tests import factories
from workbaskets.models import get_partition_scheme

pytestmark = pytest.mark.django_db
partition_scheme = get_partition_scheme()


def test_tracked_models_are_linked_to_queryset():
    """Asserts that all models returned by ``tracked_models`` are in the
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
    unordered_tracked_models = qs.tracked_models.record_ordering()

    assert (
        unordered_tracked_models.filter(
            transaction=transaction_this,
        ).count()
        == unordered_tracked_models.count()
    )


def test_tracked_models_are_sorted_correctly():
    """Asserts that all models returned by ``tracked_models`` in the right
    order, i.e. ordered first by transaction order and then in record code
    order."""
    transaction_first = factories.TransactionFactory(
        partition=TransactionPartition.DRAFT,
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
    ordered_tracked_models = qs.tracked_models.record_ordering().values(
        "transaction__partition",
        "transaction__order",
        "record_code",
        "subrecord_code",
    )

    assert sorted(
        ordered_tracked_models,
        key=lambda x: (
            x["transaction__partition"],
            x["transaction__order"],
            x["record_code"],
            x["subrecord_code"],
        ),
    ) == list(ordered_tracked_models)


def test_pre_ordering_of_querysets_with_negative_transaction_orders():
    """Asserts that querysets with negative tx orders assign negative orders to
    all transactions."""
    transaction_first = factories.TransactionFactory(order=-1)

    transaction_second = factories.TransactionFactory(order=1)

    ids = (transaction_first.id, transaction_second.id)
    qs = Transaction.objects.filter(id__in=ids)

    qs.move_to_end_of_partition(TransactionPartition.DRAFT)

    assert all(tx.order > 0 for tx in qs.all())


def test_move_end_of_partition_sets_order_and_partition():
    """
    Verify that move_to_end_of_partition moves the transaction to the end of the
    specified partition.

    Tests with negative and very large transaction numbers.
    """
    tx1 = factories.TransactionFactory(
        partition=TransactionPartition.DRAFT,
        order=-1,
    )

    tx2 = factories.TransactionFactory(
        partition=TransactionPartition.DRAFT,
        order=99,
    )

    # Create a pre-existing transaction.
    factories.TransactionFactory(partition=TransactionPartition.REVISION, order=10)

    qs = Transaction.objects.filter(id__in=(tx1.id, tx2.id))
    qs.move_to_end_of_partition(TransactionPartition.REVISION)

    qs = Transaction.objects.filter(id__in=(tx1.id, tx2.id))

    # Verify the partition was updated
    assert set(qs.values_list("partition", flat=True)) == {
        TransactionPartition.REVISION,
    }

    # Verify order has moved to the end of the partition.
    assert list(qs.values_list("pk", "order")) == [
        (tx1.pk, 11),
        (tx2.pk, 12),
    ]
