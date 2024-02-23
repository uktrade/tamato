from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import DetailView

from reference_documents.models import AlignmentReport
from reference_documents.models import AlignmentReportCheckStatus
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
            failure_count = (
                report.alignment_report_checks.all()
                .filter(status=AlignmentReportCheckStatus.FAIL)
                .count()
            )
            pass_count = (
                report.alignment_report_checks.all()
                .filter(status=AlignmentReportCheckStatus.PASS)
                .count()
            )

            if pass_count > 0:
                pass_percentage = round(
                    (pass_count / (pass_count + failure_count)) * 100,
                    2,
                )
            else:
                pass_percentage = 100

            alignment_reports.append(
                [
                    {
                        "text": report.created_at.strftime("%d/%m/%Y %H:%M"),
                    },
                    {
                        "text": pass_count,
                    },
                    {
                        "text": failure_count,
                    },
                    {
                        "text": f"{pass_percentage} %",
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
