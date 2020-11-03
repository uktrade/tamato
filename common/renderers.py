import itertools

from rest_framework.renderers import TemplateHTMLRenderer


def counter_generator():
    counter = itertools.count(start=1)
    return lambda: next(counter)


class TaricXMLRenderer(TemplateHTMLRenderer):
    media_type = "application/xml"
    format = "xml"

    def get_template_context(self, *args, **kwargs):
        context = super().get_template_context(*args, **kwargs)

        if isinstance(context, list):
            context = {"items": context, "envelope_id": counter_generator()}
        context["message_counter"] = counter_generator()
        context["counter_generator"] = counter_generator
        return context
