from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Count
from django.db.models import Q
from django.http import HttpResponse
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
from importer.models import ImportBatchStatus
from workbaskets.validators import WorkflowStatus


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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        import_status = self.request.GET.get("status")
        workbasket_status = self.request.GET.get("workbasket__status")

        context["selected_link"] = "all"

        if (
            import_status == ImportBatchStatus.SUCCEEDED
            and workbasket_status == WorkflowStatus.EDITING
        ):
            context["selected_link"] = "completed"
        elif (
            import_status == ImportBatchStatus.SUCCEEDED
            and workbasket_status == WorkflowStatus.PUBLISHED
        ):
            context["selected_link"] = "published"
        elif (
            import_status == ImportBatchStatus.SUCCEEDED
            and workbasket_status == WorkflowStatus.ARCHIVED
        ):
            context["selected_link"] = "empty"
        elif import_status == ImportBatchStatus.IMPORTING and workbasket_status == None:
            context["selected_link"] = "importing"
        elif import_status == ImportBatchStatus.FAILED and workbasket_status == None:
            context["selected_link"] = "errored"

        return context


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
    template_name = "eu-importer/import.jinja"

    def get_success_url(self):
        return reverse_lazy(
            "commodity_importer-ui-success",
            kwargs={"pk": self.object.pk},
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        self.object = form.save()

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


class DownloadAdminTaricView(RequiresSuperuserMixin, DetailView):
    model = models.ImportBatch

    def download_response(self, import_batch: models.ImportBatch) -> HttpResponse:
        """Returns a response object with associated payload containing the
        contents of `import_batch.taric_file`."""

        file_content = import_batch.taric_file.read()
        response = HttpResponse(file_content)
        response["content-type"] = "text/xml"
        response["content-length"] = len(file_content)
        response[
            "content-disposition"
        ] = f'attachment; filename="{import_batch.taric_file.name}"'
        return response

    def get(self, request, *args, **kwargs) -> HttpResponse:
        import_batch = self.get_object()
        return self.download_response(import_batch)
