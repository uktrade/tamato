from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Count
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import FormView
from django.views.generic import TemplateView

from common.views import RequiresSuperuserMixin
from common.views import WithPaginationListView
from importer import forms
from importer import models
from importer.filters import ImportBatchFilter
from importer.filters import TaricImportFilter


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


class CommodityImportView(
    PermissionRequiredMixin,
    FormView,
):
    """Commodity code import view."""

    template_name = "commodities/import.jinja"
    form_class = forms.CommodityImportForm
    success_url = reverse_lazy("commodity_importer-ui-success")
    permission_required = [
        "common.add_trackedmodel",
        "common.change_trackedmodel",
    ]

    def form_valid(self, form):
        form.save(user=self.request.user)
        return super().form_valid(form)


class CommodityImportSuccessView(TemplateView):
    """Commodity code import success view."""

    template_name = "commodities/import-success.jinja"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["saved_file_name"] = "TODO"
        context["saved_file_workbasket_id"] = "TODO"
        context["saved_batch_status"] = "TODO"

        return context


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
