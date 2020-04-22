from django.shortcuts import render

from .models import Footnote


def list_footnotes(request):
    return render(
        request, "footnotes/list.jinja", context={"footnotes": Footnote.objects.all(),}
    )
