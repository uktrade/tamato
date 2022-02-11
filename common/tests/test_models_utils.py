from unittest import mock

import pytest

from common.models.utils import LazyValue
from common.models.utils import get_current_transaction
from common.models.utils import override_current_transaction
from common.models.utils import set_current_transaction
from common.tests import factories
from common.tests.models import TestModel1
from common.tests.models import model_with_history

pytestmark = pytest.mark.django_db


@pytest.fixture
def test_model1_with_history(date_ranges):
    return model_with_history(
        factories.TestModel1Factory,
        date_ranges,
        version_group=factories.VersionGroupFactory.create(),
        sid=1,
    )


def test_lazy_value():
    counter = iter(range(10))
    val = LazyValue(get_value=lambda: next(counter))

    assert val.value == 0
    assert val.value == 1
    assert val.value == 2


def test_get_current_transaction_from_thread_locals():
    with mock.patch("common.models.utils._thread_locals") as thread_locals:
        assert get_current_transaction() is thread_locals.transaction


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


def test_current_objects_model_manager(test_model1_with_history):
    for model_version in test_model1_with_history.all_models:
        set_current_transaction(model_version.transaction)
        assert TestModel1.current_objects.count() == 1
