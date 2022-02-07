import contextlib
import threading
from typing import FrozenSet

from django.db.models import Value

_thread_locals = threading.local()


class LazyValue(Value):
    """
    Lazily evaluated Value.

    Calls a function passed to the constructor when ``value`` property is
    accessed. This allows the value to change with each access.
    """

    allow_list: FrozenSet[str] = frozenset()

    def __init__(self, **kwargs) -> None:
        self.get_value = kwargs.pop("get_value", lambda: None)
        # skip Value constructor which assigns to self.value
        super(Value, self).__init__(**kwargs)

    @property
    def value(self):
        return self.get_value()

    def __getattr__(self, name: str):
        if name not in self.allow_list:
            raise AttributeError(name)
        return type(self)(get_value=lambda: getattr(self.value, name))


class LazyTransaction(LazyValue):
    allow_list = frozenset({"order", "partition", "workbasket_id"})


def get_current_transaction():
    return getattr(_thread_locals, "transaction", None)


def set_current_transaction(transaction):
    _thread_locals.transaction = transaction


class TransactionMiddleware:
    """Middleware to set a global, current transaction prior to view
    processing."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from workbaskets.models import WorkBasket

        set_current_transaction(
            WorkBasket.get_current_transaction(request),
        )
        response = self.get_response(request)
        # No post-view processing required.
        return response


@contextlib.contextmanager
def override_current_transaction(transaction=None):
    """Override the thread-local current transaction with the specified
    transaction."""
    old_transaction = get_current_transaction()
    try:
        set_current_transaction(transaction)
        yield transaction
    finally:
        set_current_transaction(old_transaction)
