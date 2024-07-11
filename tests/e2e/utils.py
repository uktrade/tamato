from importlib import import_module
from time import time

from django.conf import settings
from django.contrib.auth import BACKEND_SESSION_KEY
from django.contrib.auth import HASH_SESSION_KEY
from django.contrib.auth import SESSION_KEY

SessionStore = import_module(settings.SESSION_ENGINE).SessionStore


def get_unique_id() -> str:
    """
    Returns the current time in seconds since the Epoch as a string.

    Useful for form fields in tests that require unique ID values.
    """
    return str(time()).replace(".", "")


def login(page, user, base_url):
    """Adds a Session cookie to a Playwright page's context for user
    authentication."""
    session = SessionStore()
    session[SESSION_KEY] = user._meta.pk.value_to_string(user)
    session[BACKEND_SESSION_KEY] = settings.AUTHENTICATION_BACKENDS[0]
    session[HASH_SESSION_KEY] = user.get_session_auth_hash()
    session.save()

    cookie = {
        "name": settings.SESSION_COOKIE_NAME,
        "value": session.session_key,
        "url": f"{base_url}/",
    }

    context = page.context
    context.add_cookies(
        [
            cookie,
        ],
    )
