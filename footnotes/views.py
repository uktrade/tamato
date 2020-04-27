from django.shortcuts import render
from rest_framework import filters
from rest_framework import permissions
from rest_framework import renderers
from rest_framework import response
from rest_framework import viewsets

from footnotes.filters import FootnoteFilter
from footnotes.models import Footnote
from footnotes.models import FootnoteType
from footnotes.serializers import FootnoteSerializer
from footnotes.serializers import FootnoteTypeSerializer


class FootnoteViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows footnotes to be viewed.
    """

    queryset = Footnote.objects.all()
    serializer_class = FootnoteSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_class = FootnoteFilter
    search_fields = ["id"]


class FootnoteUIViewSet(FootnoteViewSet):
    """
    UI endpoint that allows footnotes to be viewed.
    """

    renderer_classes = [renderers.TemplateHTMLRenderer]

    def list(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        return render(request, "footnotes/list.jinja", context={"footnotes": queryset})
