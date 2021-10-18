import pytest
from django.db.models.expressions import Value

from common.models.transactions import Transaction
from common.tests import factories
from footnotes.models import Footnote

pytestmark = pytest.mark.django_db()


fake_thread_locals = {}


def get_current_transaction():
    return fake_thread_locals["transaction"]


class CurrentTransaction(Value):
    def __init__(self, **kwargs):
        super(Value, self).__init__(None, **kwargs)

    @property
    def value(self):
        return get_current_transaction().id


def test_current_transaction_value():
    factories.TransactionFactory.create_batch(3)
    transactions = Transaction.objects.all()
    num_transactions = len(transactions)
    tx = transactions[num_transactions - 2]
    fake_thread_locals["transaction"] = tx

    qs = Footnote.objects.filter(transaction_id=CurrentTransaction())
    print(qs.query)

    assert all(f.transaction == tx for f in qs)

    new_tx = transactions[num_transactions - 1]
    fake_thread_locals["transaction"] = new_tx
    print(qs.query)

    assert all(f.transaction != tx for f in qs)
    assert all(f.transaction == new_tx for f in qs)

    assert False
