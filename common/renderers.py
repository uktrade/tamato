import itertools
from typing import Callable

from rest_framework.renderers import TemplateHTMLRenderer


Counter = Callable[[], int]


def counter_generator(start=1) -> Counter:
    counter = itertools.count(start=start)
    return lambda: next(counter)


class TaricXMLRenderer(TemplateHTMLRenderer):
    media_type = "application/xml"
    format = "xml"

    def get_template_context(self, *args, **kwargs):
        context = super().get_template_context(*args, **kwargs)

        if isinstance(context, list):
            context = {"items": context, "envelope_id": f"{counter_generator()():06}"}
        context["message_counter"] = counter_generator()
        context["counter_generator"] = counter_generator
        return context
