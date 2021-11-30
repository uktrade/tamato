import contextlib

from crum import _thread_locals
from crum import get_current_request
from django.db.models import Value


class LazyValue(Value):
    """
    Lazily evaluated Value.

    Calls a function passed to the constructor when ``value`` property is
    accessed. This allows the value to change with each access.
    """

    def __init__(self, **kwargs) -> None:
        self.get_value = kwargs.pop("get_value", lambda: None)
        # skip Value constructor which assigns to self.value
        super(Value, self).__init__(**kwargs)

    @property
    def value(self):
        return self.get_value()


def get_current_transaction():
    tx = getattr(_thread_locals, "transaction", None)

    if tx is None:
        request = get_current_request()

        if request:
            from workbaskets.models import WorkBasket

            return WorkBasket.get_current_transaction(request)

    return tx


def set_current_transaction(tx):
    # TODO doesn't try to override the session workbasket, but it could
    _thread_locals.transaction = tx


@contextlib.contextmanager
def override_current_transaction(tx=None):
    """Override the thread-local current transaction with the specified
    transaction."""
    old_current_tx = get_current_transaction()
    try:
        set_current_transaction(tx)
        yield tx
    finally:
        set_current_transaction(old_current_tx)
