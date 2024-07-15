from xml.etree.ElementTree import ParseError

from django.db.models import Count
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import DetailView
from django.views.generic import FormView

from common.views.base import WithPaginationListView
from common.views.mixins import RequiresSuperuserMixin
from importer.filters import ImportBatchFilter
from importer.models import ImportBatch
from importer.models import ImporterChunkStatus
from importer.models import ImportIssueType
from taric_parsers import forms


class TaricImportList(RequiresSuperuserMixin, WithPaginationListView):
    """UI endpoint for viewing and filtering TARIC parser imports."""

    queryset = (
        ImportBatch.objects.all()
        .order_by("-created_at")
        .annotate(
            import_issues_error_count=Count(
                "issues",
                filter=Q(issues__issue_type=ImportIssueType.ERROR),
                distinct=True,
            ),
            import_issues_warning_count=Count(
                "issues",
                filter=Q(issues__issue_type=ImportIssueType.WARNING),
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
        try:
            form.save(user=self.request.user)
        except ParseError:
            form.add_error(
                "taric_file",
                "The selected file could not be processed, please check the file and try again.",
            )
            return super().form_invalid(form)

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
