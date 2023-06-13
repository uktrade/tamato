from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Count
from django.db.models import Q
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import FormView
from django.views.generic import TemplateView

from common.views import RequiresSuperuserMixin
from common.views import WithPaginationListView
from importer import forms
from importer import models
from importer.filters import ImportBatchFilter
from importer.filters import TaricImportFilter
from workbaskets.session_store import SessionStore
from workbaskets.views.decorators import require_current_workbasket
from workbaskets.views.mixins import WithCurrentWorkBasket


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


@method_decorator(require_current_workbasket, name="dispatch")
class CommodityImportView(
    PermissionRequiredMixin,
    FormView,
    WithCurrentWorkBasket,
):
    # The correct view for importer work - shows import file form page
    template_name = "commodities/import.jinja"
    form_class = forms.CommodityImportForm
    success_url = reverse_lazy("commodity_importer-ui-success")
    permission_required = [
        "common.add_trackedmodel",
        "common.change_trackedmodel",
    ]

    @property
    def session_store(self):
        return SessionStore(
            self.request,
            f"TARIC_FILE_UPLOAD_SESSION",
        )

    def form_valid(self, form):
        session_store = self.session_store
        form.save(
            session_store,
            user=self.request.user,
            workbasket_id=self.workbasket.id,
        )
        # Add details to the session so that the success view can grab them later.
        self.session_store.add_items(
            {
                "saved_file_name": form.cleaned_data["taric_file"].name,
                "saved_file_workbasket_id": self.workbasket.id,
            },
        )
        return super().form_valid(form)


class CommodityImportSuccessView(TemplateView):
    # The correct success view for importer work.
    template_name = "commodities/import-success.jinja"

    @property
    def session_store(self):
        return SessionStore(
            self.request,
            f"TARIC_FILE_UPLOAD_SESSION",
        )

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["saved_file_name"] = self.session_store.data["saved_file_name"]
        context["saved_file_workbasket_id"] = self.session_store.data[
            "saved_file_workbasket_id"
        ]
        context["saved_batch_status"] = self.session_store.data["saved_batch_status"]

        return context


class TaricImportList(PermissionRequiredMixin, WithPaginationListView):
    """UI endpoint for viewing and filtering TARIC file imports."""

    permission_required = [
        "common.add_trackedmodel",
        "common.change_trackedmodel",
    ]
    queryset = models.ImportBatch.objects.order_by("-created_at")
    template_name = "eu-importer/select-imports.jinja"
    filterset_class = TaricImportFilter
