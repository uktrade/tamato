import pytest

from common.tests import factories
from footnotes.models import Footnote

pytestmark = pytest.mark.django_db()


class Transaction:
    def __init__(self, transaction):
        self.thread_local_transaction = transaction

    @property
    def current(self):
        return self.thread_local_transaction

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        pass


def test_transaction_context(unapproved_transaction):
    with Transaction(unapproved_transaction) as tx:
        footnotes = Footnote.objects.approved_up_to_transaction(tx.current)

        assert footnotes.count() == 0

        factories.FootnoteFactory.create(transaction=tx.current)

        assert footnotes.count() == 1
