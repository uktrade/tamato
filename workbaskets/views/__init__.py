from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from django.urls import reverse
from django.views.generic.base import RedirectView
from django.views.generic.base import TemplateView
from django.views.generic.detail import DetailView
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.list import ListView
from rest_framework import renderers
from rest_framework import viewsets

from common.renderers import TaricXMLRenderer
from workbaskets.models import WorkBasket
from workbaskets.models import get_partition_scheme
from workbaskets.serializers import WorkBasketSerializer


class WorkBasketViewSet(viewsets.ModelViewSet):
    """API endpoint that allows workbaskets to be viewed and edited."""

    queryset = WorkBasket.objects.prefetch_related("transactions")
    filterset_fields = ("status",)
    serializer_class = WorkBasketSerializer
    renderer_classes = [
        renderers.JSONRenderer,
        renderers.BrowsableAPIRenderer,
        TaricXMLRenderer,
    ]
    search_fields = ["title"]

    def get_template_names(self, *args, **kwargs):
        if self.detail:
            return ["workbaskets/taric/workbasket_detail.xml"]
        return ["workbaskets/taric/workbasket_list.xml"]


class WorkBasketList(ListView):
    """UI endpoint for viewing and filtering workbaskets."""

    model = WorkBasket
    template_name = "workbaskets/list.jinja"


class WorkBasketDetail(DetailView):
    """UI endpoint for viewing a specified workbasket."""

    model = WorkBasket
    template_name = "workbaskets/detail.jinja"


class WorkBasketSubmit(PermissionRequiredMixin, SingleObjectMixin, RedirectView):
    """UI endpoint for submitting a workbasket to HMRC CDS."""

    model = WorkBasket
    permission_required = "workbaskets.change_workbasket"

    @transaction.atomic
    def get_redirect_url(self, *args, **kwargs):
        workbasket: WorkBasket = self.get_object()

        workbasket.submit_for_approval()
        workbasket.approve(self.request.user, get_partition_scheme())
        workbasket.export_to_cds()
        workbasket.save()
        workbasket.save_to_session(self.request.session)

        return reverse("index")


class WorkBasketDeleteChanges(TemplateView):
    template_name = "workbaskets/delete_changes.jinja"

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs)
