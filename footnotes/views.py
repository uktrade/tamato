from django.shortcuts import render
from rest_framework import filters
from rest_framework import permissions
from rest_framework import renderers
from rest_framework import response
from rest_framework import viewsets

from footnotes.models import Footnote
from footnotes.models import FootnoteType
from footnotes.renderers import FootnotesAPIRenderer
from footnotes.serializers import FootnoteSerializer
from footnotes.serializers import FootnoteTypeSerializer


class FootnoteViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows footnotes to be viewed or edited.
    """

    queryset = Footnote.objects.all().order_by("id")
    serializer_class = FootnoteSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["id"]
    renderer_classes = [renderers.BrowsableAPIRenderer, FootnotesAPIRenderer]


class FootnoteUIViewSet(FootnoteViewSet):
    """
    UI endpoint that allows footnotes to be viewed or edited.
    """

    renderer_classes = [renderers.TemplateHTMLRenderer]

    def list(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        return render(request, "footnotes/list.jinja", context={"footnotes": queryset})


class FootnoteTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows footnote types to be viewed or edited.
    """

    queryset = FootnoteType.objects.all().order_by("id")
    serializer_class = FootnoteTypeSerializer
    permission_classes = [permissions.IsAuthenticated]
    renderer_classes = [renderers.BrowsableAPIRenderer, FootnotesAPIRenderer]
