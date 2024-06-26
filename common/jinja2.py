import os
import re
from datetime import datetime

from crispy_forms.utils import render_crispy_form
from django.conf import settings
from django.contrib import messages
from django.contrib.humanize.templatetags.humanize import intcomma
from django.template.defaultfilters import pluralize
from django.templatetags.static import static
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.timezone import template_localtime
from humanize import naturalsize
from jinja2.utils import markupsafe
from webpack_loader.contrib.jinja2ext import _render_bundle
from webpack_loader.templatetags.webpack_loader import webpack_static

from govuk_frontend_jinja.templates import Environment
from govuk_frontend_jinja.templates import NunjucksExtension
from workbaskets.models import WorkBasket


class GovukFrontendExtension(NunjucksExtension):
    """Builds on govuk_frontend_jinja.templates.NunjucksExtension to provide
    more template preprocessing, to fix issues translating Nunjucks templates to
    Jinja templates."""

    def preprocess(self, source, name, filename=None):
        if filename and filename.endswith(".njk"):
            source = super().preprocess(source, name, filename)

            # fix iterating objects
            # govuk_frontend_jinja only catches `params.attributes`
            iterated_objects = [
                r"item.attributes",
            ]
            source = re.sub(
                r"(for attribute, value in )(" + r"|".join(iterated_objects) + r")",
                r"\1(\2|default({}))",
                source,
            )

            # fix nested attribute access
            # NunjucksUndefined ought to catch these, but doesn't
            nested_attrs = [
                r"cell.attributes",
                r"item.conditional",
                r"item.hint",
                r"item.label",
                r"params.attributes",
                r"params.countMessage",
                r"params.formGroup",
                r"params.legend",
                r"params.prefix",
                r"params.suffix",
            ]
            source = re.sub(
                r"(" + r"|".join(nested_attrs) + r")\.",
                r"(\1|default({})).",
                source,
            )

            # fix concatenating str and int
            source = source.replace(
                "+ (params.maxlength or params.maxwords) +",
                "~ (params.maxlength or params.maxwords) ~",
            )

        return source


class GovukFrontendEnvironment(Environment):
    """Override the govuk_frontend_jinja Environment class to use our extra
    template preprocessing."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("extensions", [GovukFrontendExtension])
        super().__init__(*args, **kwargs)


def break_words(word):
    """
    Adds zero-width spaces around non-word characters to allow breaking lines
    when wrapping text.

    For example:

    >>> break_words("hello/goodbye")
    "hello&8203;/&8203;goodbye"
    """
    return markupsafe.Markup(re.sub(r"([^\w]+)", r"&#8203;\1&#8203;", word))


def query_transform(request, **kwargs):
    """Override query parameters in the current request string."""
    updated = request.GET.copy()
    for key, value in kwargs.items():
        updated[key] = value
    return updated.urlencode()


def debug_output(text):
    if settings.DEBUG:
        print(text)
    return ""


def format_date_string(date_str):
    """Parses and converts a date string from the format returned by the tariffs
    API to the one used in the TAP UI."""
    if date_str:
        date_object = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ").date()
        return date_object.strftime("%d %b %Y")
    return ""


def environment(**kwargs):
    """
    Set up the Jinja template environment.

    Add global variables and functions.
    """
    env = GovukFrontendEnvironment(**kwargs)

    env.filters.update(
        {
            "localtime": template_localtime,
            "pluralize": pluralize,
        },
    )

    env.globals.update(
        {
            "break_words": break_words,
            "query_transform": query_transform,
            "debug_output": debug_output,
            "crispy": render_crispy_form,
            "env": os.environ.get("ENV", "dev"),
            "get_messages": messages.get_messages,
            "get_current_workbasket": WorkBasket.current,
            "localtime": template_localtime,
            "mark_safe": mark_safe,
            "naturalsize": naturalsize,
            "pluralize": pluralize,
            "render_bundle": _render_bundle,
            "settings": settings,
            "static": static,
            "format_date_string": format_date_string,
            "intcomma": intcomma,
            "url": reverse,
            "webpack_static": webpack_static,
        },
    )

    return env
