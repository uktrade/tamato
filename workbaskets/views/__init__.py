from django.contrib.auth.decorators import permission_required
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.views.decorators.http import require_GET
from django_filters import rest_framework as filters
from rest_framework import renderers
from rest_framework import viewsets

from common.renderers import TaricXMLRenderer
from workbaskets.models import WorkBasket
from workbaskets.serializers import WorkBasketSerializer


class WorkBasketViewSet(viewsets.ModelViewSet):
    """API endpoint that allows workbaskets to be viewed and edited."""

    queryset = WorkBasket.objects.prefetch_related("transactions")
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_fields = ("status",)
    serializer_class = WorkBasketSerializer
    renderer_classes = [
        renderers.JSONRenderer,
        renderers.BrowsableAPIRenderer,
        TaricXMLRenderer,
    ]
    search_fields = ["title"]
    template_name = "workbaskets/taric/workbasket_list.xml"

    def get_template_names(self, *args, **kwargs):
        if self.detail:
            return ["workbaskets/taric/workbasket_detail.xml"]
        return ["workbaskets/taric/workbasket_list.xml"]


@permission_required("workbaskets.change_workbasket")
@require_GET
@transaction.atomic
def submit_workbasket_view(request, workbasket_pk):
    workbasket = get_object_or_404(WorkBasket, pk=workbasket_pk)

    workbasket.full_clean()

    workbasket.submit_for_approval()
    workbasket.approve(request.user)

    workbasket.export_to_cds()
    workbasket.save()

    return redirect("index")
