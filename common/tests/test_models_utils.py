from unittest import mock

import pytest
from crum import set_current_request

from common.models.utils import LazyValue
from common.models.utils import get_current_transaction
from common.models.utils import override_current_transaction
from common.models.utils import set_current_transaction
from common.tests import factories

pytestmark = pytest.mark.django_db


def test_lazy_value():
    counter = iter(range(10))
    val = LazyValue(get_value=lambda: next(counter))

    assert val.value == 0
    assert val.value == 1
    assert val.value == 2


def test_get_current_transaction_from_thread_locals():
    with mock.patch("common.models.utils._thread_locals") as thread_locals:
        assert get_current_transaction() is thread_locals.transaction


def test_get_current_transaction_from_request(client):
    set_current_request(client)

    with mock.patch("workbaskets.models.WorkBasket") as WorkBasket:
        tx = get_current_transaction()

        WorkBasket.get_current_transaction.assert_called_once()

        assert tx == WorkBasket.get_current_transaction.return_value


def test_set_current_transaction():
    tx = factories.TransactionFactory.create()
    assert tx is not None
    assert get_current_transaction() is None

    set_current_transaction(tx)
    assert get_current_transaction() is tx


def test_override_current_transaction():
    tx = factories.TransactionFactory.create()
    tx2 = factories.TransactionFactory.create()

    set_current_transaction(tx)

    with override_current_transaction(tx2):
        assert get_current_transaction() is tx2

    assert get_current_transaction() is tx
