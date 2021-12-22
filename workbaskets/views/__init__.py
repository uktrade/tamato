from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic.base import RedirectView
from django.views.generic.base import TemplateView
from django.views.generic.detail import DetailView
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.list import ListView
from rest_framework import renderers
from rest_framework import viewsets

from common.models import TrackedModel
from common.models import Transaction
from common.renderers import TaricXMLRenderer
from common.validators import UpdateType
from workbaskets.models import WorkBasket
from workbaskets.models import get_partition_scheme
from workbaskets.serializers import WorkBasketSerializer
from workbaskets.session_store import SessionStore


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


class WorkBasketDeleteChanges(PermissionRequiredMixin, ListView):
    template_name = "workbaskets/delete_changes.jinja"
    permission_required = "workbaskets.change_workbasket"

    def _workbasket(self):
        try:
            workbasket = WorkBasket.objects.get(pk=self.kwargs["pk"])
        except WorkBasket.DoesNotExist:
            workbasket = TrackedModel.objects.none()
        return workbasket

    def _session_store(self, workbasket):
        return SessionStore(
            self.request,
            f"WORKBASKET_SELECTIONS_{workbasket.pk}",
        )

    def _delete(self, tracked_model):
        """Delete a tracked model as deleted."""
        transaction = Transaction()
        transaction.save()
        tracked_model.update_type = UpdateType.DELETE
        tracked_model.transaction = transaction
        tracked_model.save()

    def get_queryset(self):
        """Returns the QuerySet of TrackedModels that are candidates for
        deletion."""

        workbasket = self._workbasket()
        store = self._session_store(workbasket)

        return workbasket.tracked_models.filter(pk__in=store.data.keys())

    def post(self, request, *args, **kwargs):
        if request.POST.get("action", None) != "delete":
            # User has cancelled.
            return redirect("index")

        for tracked_model in self.get_queryset():
            self._delete(tracked_model)

        workbasket = self._workbasket()
        session_store = self._session_store(workbasket)
        session_store.clear()

        redirect_url = reverse(
            "workbaskets:workbasket-ui-delete-changes-done",
            kwargs={"pk": self.kwargs["pk"]},
        )
        return redirect(redirect_url)


class WorkBasketDeleteChangesDone(TemplateView):
    template_name = "workbaskets/delete_changes_confirm.jinja"
