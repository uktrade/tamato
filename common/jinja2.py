import os
import re

from django.contrib import messages
from django.template.defaultfilters import pluralize
from django.templatetags.static import static
from django.urls import reverse
from govuk_frontend_jinja.templates import Environment
from govuk_frontend_jinja.templates import NunjucksExtension
from govuk_frontend_jinja.templates import NunjucksUndefined
from webpack_loader.templatetags.webpack_loader import render_bundle
from webpack_loader.templatetags.webpack_loader import webpack_static


class GovukFrontendExtension(NunjucksExtension):
    def preprocess(self, source, name, filename=None):
        if filename and filename.endswith(".njk"):
            source = super().preprocess(source, name, filename)

            # Additional code needed for looping over dicts in python Adds in the
            # .items() suffix, but also guards against iterating over empty dicts which
            # is something that you can "get away with" in JS but not Python
            source = re.sub(
                r"\bin (.*).attributes.items\b",
                r"in \1.get('attributes', {}).items",
                source,
            )

        return source


class GovukFrontendEnvironment(Environment):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("extensions", [GovukFrontendExtension])
        super().__init__(*args, **kwargs)


def environment(**kwargs):
    env = GovukFrontendEnvironment(**kwargs)

    env.globals.update(
        {
            "env": os.environ.get("ENV", "dev"),
            "get_messages": messages.get_messages,
            "pluralize": pluralize,
            "render_bundle": render_bundle,
            "static": static,
            "url": reverse,
            "webpack_static": webpack_static,
        }
    )

    return env
