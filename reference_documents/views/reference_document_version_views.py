from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import DetailView

from commodities.models import GoodsNomenclature
from geo_areas.models import GeographicalAreaDescription
from reference_documents.models import AlignmentReportCheckStatus
from reference_documents.models import ReferenceDocumentVersion


class ReferenceDocumentVersionDetails(PermissionRequiredMixin, DetailView):
    template_name = "reference_document_versions/new_details.jinja"
    permission_required = "reference_documents.view_reference_document"
    model = ReferenceDocumentVersion

    def get_country_by_area_id(self, area_id):
        description = (
            GeographicalAreaDescription.objects.latest_approved()
            .filter(described_geographicalarea__area_id=area_id)
            .order_by("-validity_start")
            .first()
        )
        if description:
            return description.description
        else:
            return f"{area_id} (unknown description)"

    def get_tap_comm_code(self, duty):
        if duty.reference_document_version.entry_into_force_date is not None:
            contains_date = duty.reference_document_version.entry_into_force_date
        else:
            contains_date = duty.reference_document_version.published_date

        goods = GoodsNomenclature.objects.latest_approved().filter(
            item_id=duty.commodity_code,
            valid_between__contains=contains_date,
            suffix=80,
        )

        if len(goods) == 0:
            return None

        return goods.first()

    def get_context_data(self, *args, **kwargs):
        context = super(ReferenceDocumentVersionDetails, self).get_context_data(
            *args,
            **kwargs,
        )

        # title
        context[
            "ref_doc_title"
        ] = f'Reference Document for {self.get_country_by_area_id(context["object"].reference_document.area_id)}'

        context["reference_document_version_duties_headers"] = [
            {"text": "Comm Code"},
            {"text": "Duty Rate"},
            {"text": "Validity"},
            {"text": "Checks"},
            {"text": "Actions"},
        ]

        context["reference_document_version_quotas_headers"] = [
            {"text": "Comm Code"},
            {"text": "Rate"},
            {"text": "Volume"},
            {"text": "Validity"},
            {"text": "Checks"},
            {"text": "Actions"},
        ]

        reference_document_version_duties = []
        reference_document_version_quotas = {}

        latest_alignment_report = context["object"].alignment_reports.last()

        for duty in context["object"].preferential_rates.order_by("order"):
            validity = ""

            if duty.valid_start_day:
                validity = f"{duty.valid_start_day}/{duty.valid_start_month} - {duty.valid_end_day}/{duty.valid_end_month}"

            failure_count = (
                duty.preferential_rate_checks.all()
                .filter(
                    alignment_report=latest_alignment_report,
                    status=AlignmentReportCheckStatus.FAIL,
                )
                .count()
            )

            check_count = (
                duty.preferential_rate_checks.all()
                .filter(
                    alignment_report=latest_alignment_report,
                )
                .count()
            )

            if failure_count > 0:
                checks_output = f'<div class="check-failing">FAIL</div>'
            elif check_count == 0:
                checks_output = f"N/A"
            else:
                checks_output = f'<div class="check-passing">PASS</div>'

            comm_code = self.get_tap_comm_code(duty)

            if comm_code:
                comm_code_link = f'<a class="govuk-link" href="{comm_code.get_url()}">{comm_code.item_id}</a>'
            else:
                comm_code_link = f"{duty.commodity_code}"

            reference_document_version_duties.append(
                [
                    {
                        "html": comm_code_link,
                    },
                    {
                        "text": duty.duty_rate,
                    },
                    {
                        "text": validity,
                    },
                    {
                        "html": checks_output,
                    },
                    {
                        "text": "",
                    },
                ],
            )

        # order numbers
        for quota in context["object"].preferential_quotas.order_by("order"):
            validity = ""

            if quota.valid_start_day:
                validity = f"{quota.valid_start_day}/{quota.valid_start_month} - {quota.valid_end_day}/{quota.valid_end_month}"

            failure_count = (
                quota.preferential_quota_checks.all()
                .filter(
                    alignment_report=latest_alignment_report,
                    status=AlignmentReportCheckStatus.FAIL,
                )
                .count()
            )

            check_count = (
                quota.preferential_quota_checks.all()
                .filter(
                    alignment_report=latest_alignment_report,
                )
                .count()
            )

            if failure_count > 0:
                checks_output = f'<div class="check-failing">FAIL</div>'
            elif check_count == 0:
                checks_output = f"N/A"
            else:
                checks_output = f'<div class="check-passing">PASS</div>'

            comm_code = self.get_tap_comm_code(quota)
            if comm_code:
                comm_code_link = f'<a class="govuk-link" href="{comm_code.get_url()}">{comm_code.structure_code}</a>'
            else:
                comm_code_link = f"{quota.commodity_code}"

            row_to_add = [
                {
                    "html": comm_code_link,
                },
                {
                    "text": quota.quota_duty_rate,
                },
                {
                    "text": f"{quota.volume} {quota.measurement}",
                },
                {
                    "text": validity,
                },
                {
                    "html": checks_output,
                },
                {
                    "text": "",
                },
            ]

            if quota.quota_order_number in reference_document_version_quotas.keys():
                reference_document_version_quotas[quota.quota_order_number].append(
                    row_to_add,
                )
            else:
                reference_document_version_quotas[quota.quota_order_number] = [
                    row_to_add,
                ]

        context["reference_document_version_duties"] = reference_document_version_duties

        context["reference_document_version_quotas"] = reference_document_version_quotas

        return context
