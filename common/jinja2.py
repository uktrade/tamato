import os
import re

from django.contrib import messages
from django.template.defaultfilters import pluralize
from django.templatetags.static import static
from django.urls import reverse
from govuk_frontend_jinja.templates import Environment
from govuk_frontend_jinja.templates import NunjucksExtension
from webpack_loader.templatetags.webpack_loader import render_bundle
from webpack_loader.templatetags.webpack_loader import webpack_static

from workbaskets.models import WorkBasket


class GovukFrontendExtension(NunjucksExtension):
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
                r"item.conditional",
                r"item.hint",
                r"item.label",
                r"params.attributes",
                r"params.countMessage",
                r"params.formGroup",
                r"params.legend",
            ]
            source = re.sub(
                r"(" + r"|".join(nested_attrs) + r")\.", r"(\1|default({})).", source
            )

            # fix concatenating str and int
            source = source.replace(
                "+ (params.maxlength or params.maxwords) +",
                "~ (params.maxlength or params.maxwords) ~",
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
            "get_current_workbasket": WorkBasket.current,
            "pluralize": pluralize,
            "render_bundle": render_bundle,
            "static": static,
            "url": reverse,
            "webpack_static": webpack_static,
        }
    )

    return env
