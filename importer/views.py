import uuid

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Count
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse
from django.urls import reverse_lazy
from django.views.generic import DetailView
from django.views.generic import FormView

from common.views import RequiresSuperuserMixin
from common.views import WithPaginationListView
from importer import forms
from importer import models
from importer.filters import ImportBatchFilter
from importer.filters import TaricImportFilter
from workbaskets.models import WorkBasket


class ImportBatchList(RequiresSuperuserMixin, WithPaginationListView):
    """UI endpoint for viewing and filtering General Import Batches."""

    queryset = (
        models.ImportBatch.objects.all()
        .order_by("-created_at")
        .annotate(
            chunks_done=Count(
                "chunks",
                filter=Q(chunks__status=models.ImporterChunkStatus.DONE),
            ),
            chunks_running=Count(
                "chunks",
                filter=Q(chunks__status=models.ImporterChunkStatus.RUNNING),
            ),
            chunks_waiting=Count(
                "chunks",
                filter=Q(chunks__status=models.ImporterChunkStatus.WAITING),
            ),
            chunks_errored=Count(
                "chunks",
                filter=Q(chunks__status=models.ImporterChunkStatus.ERRORED),
            ),
        )
    )
    template_name = "importer/list.jinja"
    filterset_class = ImportBatchFilter


class UploadTaricFileView(RequiresSuperuserMixin, FormView):
    form_class = forms.UploadTaricForm
    fields = ["name", "split_job"]
    success_url = reverse_lazy("import_batch-ui-list")
    template_name = "importer/create.jinja"

    def form_valid(self, form):
        form.save(user=self.request.user)
        return super().form_valid(form)


class CommodityImportListView(
    PermissionRequiredMixin,
    WithPaginationListView,
):
    """UI endpoint for viewing and filtering TARIC file imports."""

    permission_required = [
        "common.add_trackedmodel",
        "common.change_trackedmodel",
    ]
    queryset = models.ImportBatch.objects.order_by("-created_at")
    template_name = "eu-importer/select-imports.jinja"
    filterset_class = TaricImportFilter


class CommodityImportCreateView(
    PermissionRequiredMixin,
    FormView,
):
    """Commodity code file import view."""

    form_class = forms.CommodityImportForm
    permission_required = [
        "common.add_trackedmodel",
        "common.change_trackedmodel",
    ]
    success_url = reverse_lazy("commodity_importer-ui-success")
    template_name = "eu-importer/import.jinja"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        unique_id = str(uuid.uuid4())
        workbasket = WorkBasket.objects.create(
            title=f"Commodity codes import - {unique_id}",
            author=self.request.user,
        )
        self.object = form.save(workbasket)
        workbasket.reason = (
            f"Imported from file {self.object.name} - "
            f"pending review and completion."
        )
        workbasket.save()

        return redirect(
            reverse(
                "commodity_importer-ui-create-success",
                kwargs={"pk": self.object.pk},
            ),
        )


class CommodityImportCreateSuccessView(DetailView):
    """Commodity code import success view."""

    template_name = "eu-importer/import-success.jinja"
    model = models.ImportBatch
