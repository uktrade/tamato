from django.contrib.auth.decorators import permission_required
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
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


class WorkBasketUIViewSet(WorkBasketViewSet):
    """UI endpoint that allows workbaskets to be viewed and edited."""

    renderer_classes = [renderers.TemplateHTMLRenderer]

    def list(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        return render(
            request,
            "workbaskets/list.jinja",
            context={"workbaskets": queryset},
        )

    def retrieve(self, request, *args, **kwargs):
        # XXX needs updating to use TrackedModel
        # items = self.get_object().items.prefetch_related("existing_record").all()
        # groups = dict()
        # for item in items:
        #     group_name = item.existing_record.__class__._meta.verbose_name_plural
        #     groups.setdefault(group_name, []).append(item.existing_record)
        # groups = sorted(list(groups.items()), key=lambda tup: tup[0])
        groups = []
        return render(
            request,
            "workbaskets/detail.jinja",
            context={"workbasket": self.get_object(), "workbasketitem_groups": groups},
        )


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
