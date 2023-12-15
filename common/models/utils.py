import contextlib
import threading
from typing import FrozenSet

import wrapt
from django.db.models import Value
from django.http import HttpResponseRedirect
from django.urls import reverse

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
    that should be handled in this way. `allow_list` provides this set of
    attributes and should be overridden by subclasses of LazyValue. See
    `LazyTransaction.allow_list` for an example of how this is implemented for a
    `LazyValue` subclass that supports lazily evaluated Transaction instances.
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
        return self.func()


@wrapt.decorator
def lazy_string(wrapped, instance, *args, **kwargs):
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


def is_session_workbasket_valid(request):
    """Returns True if the workbasket in the session is valid (i.e. exists and
    has status EDITING.)"""
    from workbaskets.models import WorkBasket
    from workbaskets.validators import WorkflowStatus

    try:
        workbasket = WorkBasket.current(request)
        if not workbasket:
            return False
        return workbasket.status == WorkflowStatus.EDITING
    except WorkBasket.DoesNotExist:
        return False


def has_workbasket_status_changed(request):
    """Returns True if there is a workbasket in the session which is not in
    EDITING."""
    from workbaskets.models import WorkBasket
    from workbaskets.validators import WorkflowStatus

    if "workbasket" in request.session:
        print("workbasket found in session data")
        workbasket = WorkBasket.load_from_session(request.session)
        print("able to load workbasket from session")
        if workbasket.status != WorkflowStatus.EDITING:
            return True
    return False


class ValidateSessionWorkBasketMiddleware:
    """
    WorkBasket middleware that:

        - Validates that any workbasket in the user's session is valid.
        - Removes invalid workbaskets from the user's session.

    This middleware should always be placed before any other middleware in
    settings.MIDDLEWARE that references session workbaskets (for instance,
    TransactionMiddleware).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from workbaskets.models import WorkBasket

        # A current, editable workbasket is necessary in order to set the
        # current transaction (below), so abandon this middleware's action and
        # return early if there is no current editable workbasket in the
        # session.
        if has_workbasket_status_changed(request):
            WorkBasket.remove_current_from_session(request.session)
            return HttpResponseRedirect(reverse("workbasket-not-active"))

        if not is_session_workbasket_valid(request):
            WorkBasket.remove_current_from_session(request.session)
        return self.get_response(request)


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


class GetTabURLMixin:
    """Used for models whose information in the UI is displayed in a tab on the
    page of their related model."""

    url_pattern_name_prefix = ""
    url_suffix = "#"
    url_relation_field = ""

    def get_url(self, action: str = "detail") -> str:
        """Generate a URL to a representation of the model in the webapp."""
        if action == "detail":
            url = reverse(
                f"{self.get_url_pattern_name_prefix()}-ui-detail",
                kwargs={"sid": getattr(self, self.url_relation_field).sid},
            )
            return f"{url}{self.url_suffix}"
        return super().get_url(action)
