import pytest
from pytest_django.asserts import assertQuerysetEqual

from common.tests import factories
from workbaskets.models import WorkBasket

pytestmark = pytest.mark.django_db


def test_workbasket_transactions():
    workbasket = factories.WorkBasketFactory.create()
    tx1 = workbasket.new_transaction(composite_key="test1")

    with tx1:
        measure = factories.MeasureFactory.create()

    assert measure.transaction == tx1
    assert workbasket.transactions.count() == 1

    tx2 = workbasket.new_transaction(composite_key="test2")
    assert workbasket.transactions.first() == tx1

    with tx2:
        assoc = factories.FootnoteAssociationMeasureFactory.create(
            footnoted_measure=measure,
        )

    assert assoc.transaction == tx2
    assert assoc.associated_footnote.transaction == tx2
    assert workbasket.transactions.count() == 2


def test_envelope_of_transactions_populates_envelope(
    approved_workbasket, populate_workbasket
):
    """
    Workbasket.envelope_of_transactions create an envelope containing
    the same transactions as the workbasket.
    """
    populate_workbasket(approved_workbasket)
    approved_workbasket_transactions = approved_workbasket.transactions.all()
    assert approved_workbasket_transactions

    envelope = WorkBasket.objects.filter(
        pk=approved_workbasket.pk
    ).envelope_of_transactions()
    envelope_transactions = envelope.transactions.all()

    # TODO - once order is implemented for envelope transactions, check it.
    assert set(approved_workbasket_transactions) == set(envelope_transactions)
