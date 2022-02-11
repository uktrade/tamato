import boto3
from botocore.client import Config
from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import ProtectedError
from django.http import Http404
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic.base import RedirectView
from django.views.generic.base import TemplateView
from django.views.generic.detail import DetailView
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.list import ListView
from rest_framework import renderers
from rest_framework import viewsets

from common.renderers import TaricXMLRenderer
from exporter.models import Upload
from workbaskets import tasks
from workbaskets.models import WorkBasket
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

    def get_redirect_url(self, *args, **kwargs) -> str:
        return reverse("index")

    def get(self, *args, **kwargs):
        workbasket: WorkBasket = self.get_object()

        (
            tasks.transition.si(
                workbasket.pk,
                "submit_for_approval",
            )
            | tasks.transition.si(
                workbasket.pk,
                "approve",
                self.request.user.pk,
                settings.TRANSACTION_SCHEMA,
            )
        ).delay()

        return super().get(*args, **kwargs)


class WorkBasketDeleteChanges(PermissionRequiredMixin, ListView):
    """UI for user review of WorkBasket item deletion."""

    template_name = "workbaskets/delete_changes.jinja"
    permission_required = "workbaskets.change_workbasket"

    def _workbasket(self):
        """Get the WorkBasket instance associated with this view's deletion."""

        try:
            workbasket = WorkBasket.objects.get(pk=self.kwargs["pk"])
        except WorkBasket.DoesNotExist:
            workbasket = WorkBasket.objects.none()
        return workbasket

    def _session_store(self, workbasket):
        """Get the current user's SessionStore for the WorkBasket that they're
        deleting, containing ids of the items that have been selected for
        deletion."""

        return SessionStore(
            self.request,
            f"WORKBASKET_SELECTIONS_{workbasket.pk}",
        )

    def get_queryset(self):
        """Get TrackedModelQuerySet of instances that are candidates for
        deletion."""

        workbasket = self._workbasket()
        store = self._session_store(workbasket)
        return workbasket.tracked_models.filter(pk__in=store.data.keys())

    def post(self, request, *args, **kwargs):
        if request.POST.get("action", None) != "delete":
            # The user has cancelled out of the deletion process.
            return redirect("index")

        # By reverse ordering on record_code + subrecord_code we're able to
        # delete child entities first, avoiding protected foreign key
        # violations.
        object_list = (
            self.get_queryset()
            .annotate_record_codes()
            .order_by("record_code", "subrecord_code")
            .reverse()
        )

        for obj in object_list:
            # Unlike situations where TrackedModels are superceded and are
            # subject to UpdateType.DELETE, WorkBasket item deletion really
            # should remove rows from the DB.
            try:
                obj.delete()
            except ProtectedError:
                # TODO Capture deletion failure and present back to UI.
                # UI component(s) design in the backlog for this: TP-1148.
                pass

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


def download_envelope(request):
    """
    Creates s3 resource using AWS environment variables.

    Tries to get filename from most recent s3 upload. If no upload exists, returns 404.

    Generates presigned url from s3 client using bucket and file names.

    Returns `HttpResponseRedirect` with presigned url passed as only argument.
    """
    s3 = boto3.resource(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
    )

    try:
        last_added = (
            settings.HMRC_STORAGE_DIRECTORY
            + Upload.objects.latest("created_date").filename
        )
    except Upload.DoesNotExist as err:
        raise Http404("No uploaded envelope available for download")

    url = s3.meta.client.generate_presigned_url(
        ClientMethod="get_object",
        ExpiresIn=3600,
        Params={
            "Bucket": settings.HMRC_STORAGE_BUCKET_NAME,
            "Key": last_added,
        },
    )

    return HttpResponseRedirect(url)
