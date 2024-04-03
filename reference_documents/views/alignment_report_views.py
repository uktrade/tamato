from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import DetailView

from reference_documents.models import ReferenceDocumentVersion


class ReferenceDocumentVersionAlignmentReportsDetailsView(
    PermissionRequiredMixin,
    DetailView,
):
    template_name = "reference_document_versions/alignment_reports.jinja"
    permission_required = "reference_documents.view_reference_document"
    model = ReferenceDocumentVersion

    def get_context_data(self, *args, **kwargs):
        context = super(
            ReferenceDocumentVersionAlignmentReportsDetailsView,
            self,
        ).get_context_data(
            *args,
            **kwargs,
        )

        context["alignment_report_headers"] = [
            {"text": "Created"},
            {"text": "Passed"},
            {"text": "failed"},
            {"text": "Percent"},
            {"text": "Actions"},
        ]

        alignment_reports = []
        for report in context["object"].alignment_reports.order_by("-created_at"):
            alignment_reports.append(
                [
                    {
                        "text": report.created_at.strftime("%d/%m/%Y %H:%M"),
                    },
                    {
                        "html": f"<a href='/alignment_reports/{report.pk}'>Details</a>",
                    },
                ],
            )

        context["alignment_reports"] = alignment_reports

        return context


class AlignmentReportsDetailsView(PermissionRequiredMixin, DetailView):
    template_name = "alignment_reports/details.jinja"
    permission_required = "reference_documents.view_reference_document"
    model = AlignmentReport

    def get_context_data(self, *args, **kwargs):
        context = super(AlignmentReportsDetailsView, self).get_context_data(
            *args,
            **kwargs,
        )
