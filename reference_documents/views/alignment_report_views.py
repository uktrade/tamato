from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import DetailView

from reference_documents.models import AlignmentReport
from reference_documents.models import AlignmentReportCheck


class AlignmentReportContext:
    def __init__(self, alignment_report: AlignmentReport):
        self.alignment_report = alignment_report

    def headers(self):
        return [
            {"text": "Type"},
            {"text": "Message"},
            {"text": "Status"},
        ]

    def get_links(self, alignment_report_check: AlignmentReportCheck):
        html = ""

        if alignment_report_check.ref_rate:
            html += " Pref Rate"

        if alignment_report_check.ref_order_number:
            html += " Order Number"

        if alignment_report_check.ref_quota_definition:
            html += " Pref Quota"

        if alignment_report_check.ref_quota_definition_range:
            html += " Pref Quota Template"

        if alignment_report_check.ref_quota_suspension:
            html += " Order Number..."

        if alignment_report_check.ref_quota_suspension_range:
            html += " Pref Suspension"

        return html

    def get_actions(self, alignment_report_check: AlignmentReportCheck):

        html = "Mark "

        return html

    def rows(self):
        rows = []
        for (
            alignment_report_check
        ) in self.alignment_report.alignment_report_checks.all():

            row_data = [
                {
                    "text": alignment_report_check.check_name,
                },
                {
                    "text": alignment_report_check.message,
                },
                {
                    "text": alignment_report_check.status,
                },
            ]
            rows.append(row_data)

        return rows


class AlignmentReportDetails(PermissionRequiredMixin, DetailView):
    template_name = "reference_documents/alignment_reports/details.jinja"
    permission_required = "reference_documents.view_view_alignmentreport"
    model = AlignmentReport

    def get_context_data(self, *args, **kwargs):
        context = super(AlignmentReportDetails, self).get_context_data(
            *args,
            **kwargs,
        )

        # row data
        context["reference_document_version"] = kwargs[
            "object"
        ].reference_document_version

        alignment_report_ctx = AlignmentReportContext(self.object)
        context["alignment_check_table_headers"] = alignment_report_ctx.headers()
        context["alignment_check_table_rows"] = alignment_report_ctx.rows()
        return context
