import os
import tempfile

import boto3
from botocore.client import Config
from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from django.db.models import ProtectedError
from django.http import HttpResponse
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
from exporter.tasks import send_upload_notifications
from exporter.tasks import upload_workbasket_envelopes
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

        workbasket_ids = [workbasket.id]

        upload = (
            upload_workbasket_envelopes.s(
                upload_status_data={},
                workbasket_ids=workbasket_ids,
            )
            | send_upload_notifications.s()
        )
        # transaction.on_commit(lambda:
        #     upload.delay())
        upload.delay()

        return reverse("index")


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
    get_last_modified = lambda obj: int(obj.last_modified.strftime("%s"))
    s3 = boto3.resource(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
    )
    bucket = s3.Bucket(settings.HMRC_STORAGE_BUCKET_NAME)

    last_added = [
        obj for obj in sorted(bucket.objects.all(), key=get_last_modified, reverse=True)
    ][0]

    with tempfile.NamedTemporaryFile() as f:
        bucket.download_file(last_added.key, f.name)
        with open(f.name, "rb") as fh:
            response = HttpResponse(fh.read(), content_type="text/xml")
            response[
                "Content-Disposition"
            ] = "attachment; filename=" + os.path.basename(last_added.key)

            return response
