from django.db.models import Count
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import DetailView
from django.views.generic import FormView

from common.views import RequiresSuperuserMixin
from common.views import WithPaginationListView
from importer.filters import ImportBatchFilter
from importer.models import *
from taric_parsers import forms


class TaricImportList(RequiresSuperuserMixin, WithPaginationListView):
    """UI endpoint for viewing and filtering TARIC parser imports."""

    queryset = (
        ImportBatch.objects.all()
        .order_by("-created_at")
        .annotate(
            running_chunks=Count(
                "chunks",
                filter=Q(chunks__status=ImporterChunkStatus.RUNNING),
                distinct=True,
            ),
            pending_chunks=Count(
                "chunks",
                filter=Q(chunks__status=ImporterChunkStatus.WAITING),
                distinct=True,
            ),
            errored_chunks=Count(
                "chunks",
                filter=Q(chunks__status=ImporterChunkStatus.ERRORED),
                distinct=True,
            ),
            import_issues=Count(
                "issues",
                distinct=True,
            ),
            completed_chunks=Count(
                "chunks",
                filter=Q(chunks__status=ImporterChunkStatus.DONE),
                distinct=True,
            ),
        )
    )

    template_name = "taric_parser/list.jinja"
    filterset_class = ImportBatchFilter


class TaricImportUpload(RequiresSuperuserMixin, FormView):
    form_class = forms.UploadTaricForm
    fields = ["name"]
    success_url = reverse_lazy("taric_parser_import_ui_list")
    template_name = "taric_parser/create.jinja"

    def form_valid(self, form):
        form.save(user=self.request.user)
        return super().form_valid(form)


class TaricImportDetails(RequiresSuperuserMixin, DetailView):
    """UI endpoint for viewing details of a TARIC parser import, and view
    failures and errors."""

    model = ImportBatch
    queryset = ImportBatch.objects.all()
    template_name = "taric_parser/details.jinja"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["issues"] = context["object"].issues.all()
        return context
