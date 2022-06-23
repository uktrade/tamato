import contextlib
import threading
from typing import FrozenSet

import wrapt
from django.db.models import Value

_thread_locals = threading.local()


class LazyValue(Value):
    """
    Lazily evaluated Value.

    Calls a function passed to the constructor when ``value`` property is
    accessed. This allows the value to change with each access.
    """

    allow_list: FrozenSet[str] = frozenset()
    """
    Before `LazyValue` instances are evaluated, we allow access to the proxied
    value's attributes by returning them from `__getattr__()` as `LazyValue`
    instances themselves.
    It is only possible to do this by knowing in advance the set of attributes
    that should be handled in this way.
    `allow_list` provides this set of attributes and should be overridden by
    subclasses of LazyValue.
    See `LazyTransaction.allow_list` for an example of how this is implemented
    for a `LazyValue` subclass that supports lazily evaluated Transaction
    instances.
    """

    def __init__(self, **kwargs) -> None:
        self.get_value = kwargs.pop("get_value", lambda: None)
        # skip Value constructor which assigns to self.value
        super(Value, self).__init__(**kwargs)

    @property
    def value(self):
        return self.get_value()

    def __getattr__(self, name: str):
        """Return attributes on the proxied value themselves as `LazyValue`
        instances."""

        if name not in self.allow_list:
            raise AttributeError(name)
        return type(self)(get_value=lambda: getattr(self.value, name))


class LazyTransaction(LazyValue):
    """Proxy to support lazily evaluated Transaction instances."""

    allow_list = frozenset({"order", "partition", "workbasket_id"})


class LazyString:
    """
    Wrapper around a function that returns a string.

    Useful for logging messages that are expensive to construct.
    """

    def __init__(self, func):
        self.func = func

    def __str__(self):
        return str(self.func())


@wrapt.decorator
def lazy_string(wrapped, instance, *args, **kwargs):
    """Decorator that will evaluate the wrapped function when stringified."""
    return LazyString(wrapped)


def get_current_transaction():
    return getattr(_thread_locals, "transaction", None)


def set_current_transaction(transaction):
    _thread_locals.transaction = transaction


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


class TransactionMiddleware:
    """Middleware that sets the global, current transaction for the duration of
    view processing (and processing of other middleware that follows this
    middleware in the chain)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from workbaskets.models import WorkBasket

        with override_current_transaction(
            WorkBasket.get_current_transaction(request),
        ):
            response = self.get_response(request)
        # No post-view processing required.
        return response
