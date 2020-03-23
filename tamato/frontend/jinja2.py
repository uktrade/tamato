import os

import jinja2
from django.contrib import messages
from django.templatetags.static import static
from django.urls import reverse


def environment(**kwargs):
    env = jinja2.Environment(**kwargs)

    env.globals.update(
        {
            "env": os.environ.get("ENV", "dev"),
            "get_messages": messages.get_messages,
            "static": static,
            "url": reverse,
        }
    )

    return env
