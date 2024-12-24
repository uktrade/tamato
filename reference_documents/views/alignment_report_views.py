from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import redirect
from django.views.generic import DetailView

from reference_documents.check.check_runner import Checks
from reference_documents.models import AlignmentReport, AlignmentReportCheck

# Need these loaded to find the correct check when rerunning checks
from reference_documents.check.base import BaseCheck # noqa
from reference_documents.check.base import BaseOrderNumberCheck # noqa
from reference_documents.check.base import BaseQuotaDefinitionCheck # noqa
from reference_documents.check.base import BaseQuotaSuspensionCheck # noqa
from reference_documents.check.base import BaseRateCheck # noqa
from reference_documents.check.ref_order_numbers import OrderNumberChecks  # noqa
from reference_documents.check.ref_quota_definitions import (  # noqa
    QuotaDefinitionChecks,
)
from reference_documents.check.ref_quota_suspensions import (  # noqa
    QuotaSuspensionChecks,
)
from reference_documents.check.ref_rates import RateChecks  # noqa


class AlignmentReportContext:
    def __init__(self, alignment_report: AlignmentReport):
        self.alignment_report = alignment_report

    def headers(self):
        return [
            {"text": "Type"},
            {"text": "last updated"},
            {"text": "Year"},
            {"text": "Message"},
            {"text": "Status"},
            {"text": "Actions"},
        ]

    def rows(self):
        rows = []

        for alignment_report_check in self.alignment_report.alignment_report_checks.all().order_by('target_start_date'):
            actions = (
                f'<a href="/reference_document_versions/{self.alignment_report.reference_document_version.id}/'
                f'alignment-reports/{self.alignment_report.id}/re-run-check/'
                f'{alignment_report_check.id}">Rerun check</a><br>'
            )

            row_data = [
                {
                    "text": alignment_report_check.check_name,
                },
                {
                    "text": alignment_report_check.updated_at,
                },
                {
                    "text": alignment_report_check.target_start_date.year,
                },
                {
                    "text": alignment_report_check.message,
                },
                {
                    "text": alignment_report_check.status,
                },
                {
                    "html": actions
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

class AlignmentReportRerunCheckDetails(PermissionRequiredMixin, DetailView):
    template_name = "reference_documents/alignment_reports/rerun_check.jinja"
    permission_required = "reference_documents.view_view_alignmentreport"
    model = AlignmentReportCheck

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(object=self.object)

        # get check
        check_class = self.get_check_class_by_name(self.object.check_name)
        args = {}
        if self.object.ref_rate:
            args['ref_rate'] = self.object.ref_rate

        if self.object.ref_order_number:
            args['ref_order_number'] = self.object.ref_order_number

        if self.object.ref_quota_definition:
            args['ref_quota_definition'] = self.object.ref_quota_definition

        if self.object.ref_quota_suspension:
            args['ref_quota_suspension'] = self.object.ref_quota_suspension

        check = check_class(**args)

        status, message = check.run_check()

        self.object.status = status
        self.object.message = message
        self.object.save()

        return redirect("reference_documents:alignment-report-details", version_pk=self.object.alignment_report.reference_document_version.pk, pk=self.object.alignment_report.pk)

    def get_context_data(self, *args, **kwargs):
        context = super(AlignmentReportRerunCheckDetails, self).get_context_data(
            *args,
            **kwargs,
        )

        # row data
        context["reference_document_version"] = kwargs[
            "object"
        ].alignment_report.reference_document_version
        return context

    def get_check_class_by_name(self, name):
        for ref_rate_check in Checks.get_checks_for(BaseRateCheck):
            if ref_rate_check.name == name:
                return ref_rate_check

        for order_number_check in Checks.get_checks_for(BaseOrderNumberCheck):
            if order_number_check.name == name:
                return order_number_check

        for quota_definition_check in Checks.get_checks_for(
                BaseQuotaDefinitionCheck,
        ):
            if quota_definition_check.name == name:
                return quota_definition_check

        for quota_suspension_check in Checks.get_checks_for(
                BaseQuotaSuspensionCheck,
        ):
            if quota_suspension_check.name == name:
                return quota_suspension_check

        return None
