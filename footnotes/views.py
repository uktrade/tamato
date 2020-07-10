from django.shortcuts import render
from rest_framework import permissions
from rest_framework import renderers
from rest_framework import viewsets

from footnotes.filters import FootnoteFilterBackend
from footnotes.models import Footnote
from footnotes.models import FootnoteType
from footnotes.serializers import FootnoteSerializer
from footnotes.serializers import FootnoteTypeSerializer


class FootnoteViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows footnotes to be viewed.
    """

    queryset = Footnote.objects.all().prefetch_related("descriptions")
    serializer_class = FootnoteSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [FootnoteFilterBackend]
    search_fields = [
        "footnote_id",
        "footnote_type__footnote_type_id",
        "descriptions__description",
        "footnote_type__description",
    ]


class FootnoteUIViewSet(FootnoteViewSet):
    """
    UI endpoint that allows footnotes to be viewed.
    """

    renderer_classes = [renderers.TemplateHTMLRenderer]

    def list(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        return render(
            request, "footnotes/list.jinja", context={"object_list": queryset}
        )

    def retrieve(self, request, *args, **kwargs):
        return render(
            request, "footnotes/detail.jinja", context={"object": self.get_object()}
        )


class FootnoteTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows footnote types to be viewed or edited.
    """

    queryset = FootnoteType.objects.all().prefetch_related(
        "footnotetypedescription_set"
    )
    serializer_class = FootnoteTypeSerializer
    permission_classes = [permissions.IsAuthenticated]
