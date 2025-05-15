from rest_framework import permissions
from rest_framework import renderers
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from common.renderers import TaricXMLRenderer
from common.serializers import AutoCompleteSerializer
from workbaskets.filters import WorkBasketAutoCompleteFilterBackEnd
from workbaskets.models import WorkBasket
from workbaskets.serializers import WorkBasketSerializer


class WorkBasketViewSet(viewsets.ModelViewSet):
    """API endpoint that allows workbaskets to be viewed and edited."""

    queryset = WorkBasket.objects.all()
    filterset_fields = ("status",)
    serializer_class = WorkBasketSerializer
    renderer_classes = [
        renderers.JSONRenderer,
        renderers.BrowsableAPIRenderer,
        TaricXMLRenderer,
    ]
    permission_classes = [
        permissions.IsAuthenticated,
        permissions.DjangoModelPermissions,
    ]
    search_fields = ["title"]

    # TODO: Required? Delete?
    # def get_template_names(self, *args, **kwargs):
    #    if self.detail:
    #        return ["workbaskets/taric/workbasket_detail.xml"]
    #    elif self.list:
    #        return ["workbaskets/taric/workbasket_list.xml"]
    #    else:
    #        return super().get_template_names(*args, **kwargs)
    #
    # Is this method actually ever used? If it is, then should that
    # implementation ^ actually inspect the `action` attr? Like so:
    # def get_template_name(self, *args, **kwargs):
    #    if self.action == 'detail':
    #        return ["workbaskets/taric/workbasket_detail.xml"]
    #    elif self.action == 'list':
    #        return ["workbaskets/taric/workbasket_list.xml"]
    #    else:
    #        return super().get_template_names(*args, **kwargs)

    @action(
        detail=False,
        methods=["GET"],
        url_path="autocomplete",
        url_name="autocomplete-list",
    )
    def autocomplete(self, request):
        """
        Read-only API endpoint that allows users to search for workbaskets by
        ID, title or reason (i.e description) using an autocomplete form field.

        It returns a paginated JSON array of workbaskets that match the search
        query.
        """
        filter_backend = WorkBasketAutoCompleteFilterBackEnd()
        queryset = filter_backend.filter_queryset(
            request,
            WorkBasket.objects.all(),
            self,
        )

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = AutoCompleteSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = AutoCompleteSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
