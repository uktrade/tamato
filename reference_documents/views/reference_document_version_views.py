from django.contrib.auth.mixins import PermissionRequiredMixin
from django.urls import reverse
from django.urls import reverse_lazy
from django.views.generic import DetailView
from django.views.generic import UpdateView

from commodities.models import GoodsNomenclature
from geo_areas.models import GeographicalAreaDescription
from quotas.models import QuotaOrderNumber
from reference_documents.models import AlignmentReportCheckStatus
from reference_documents.models import ReferenceDocumentVersion


class ReferenceDocumentVersionDetails(PermissionRequiredMixin, DetailView):
    template_name = "reference_documents/reference_document_versions/details.jinja"
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

    def get_tap_order_number(self, quota):
        # todo: This needs to consider the validity period(s)
        # may need to handle in the pre processing of the data e.g. where the volume defines multiple periods

        if quota.reference_document_version.entry_into_force_date is not None:
            contains_date = quota.reference_document_version.entry_into_force_date
        else:
            contains_date = quota.reference_document_version.published_date

        quota_order_number = QuotaOrderNumber.objects.latest_approved().filter(
            order_number=quota.quota_order_number,
            valid_between__contains=contains_date,
        )

        if len(quota_order_number) == 0:
            return None

        return quota_order_number.first()

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

        for duty in context["object"].preferential_rates.order_by("commodity_code"):
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
                        "text": duty.valid_between,
                    },
                    {
                        "html": checks_output,
                    },
                    {
                        "html": f"<a href='{reverse('reference_documents:preferential_rates_edit', args=[duty.pk])}'>Edit</a> "
                        f"<a href='{reverse('reference_documents:preferential_rates_delete', args=[duty.pk])}'>Delete</a>",
                    },
                ],
            )

        # order numbers
        for quota in context["object"].preferential_quotas.order_by("order"):
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

            quota_order_number = self.get_tap_order_number(quota)

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
                    "text": quota.valid_between,
                },
                {
                    "html": checks_output,
                },
                {
                    "html": f"<a href='{reverse('reference_documents:preferential_quotas_edit', args=[quota.pk])}'>Edit</a> "
                    f"<a href='{reverse('reference_documents:preferential_quotas_delete', args=[quota.pk])}'>Delete</a>",
                },
            ]

            if quota.quota_order_number in reference_document_version_quotas.keys():
                reference_document_version_quotas[quota.quota_order_number][
                    "data_rows"
                ].append(
                    row_to_add,
                )
            else:
                reference_document_version_quotas[quota.quota_order_number] = {
                    "data_rows": [row_to_add],
                    "quota_order_number": quota_order_number,
                }

        context["reference_document_version_duties"] = reference_document_version_duties
        context["reference_document_version_quotas"] = reference_document_version_quotas

        return context


class ReferenceDocumentVersionEditView(PermissionRequiredMixin, UpdateView):
    template_name = "reference_document_versions/edit.jinja"
    permission_required = "reference_documents.edit_reference_document"
    model = ReferenceDocumentVersion
    fields = ["version", "published_date", "entry_into_force_date"]

    # def post(self, request, *args, **kwargs):
    #     reference_document_version = self.get_object()
    #     reference_document_version.save()
    #     return redirect(reverse("reference_documents:details", args=[reference_document_version.reference_document.pk]))

    def form_valid(self, form):
        return super(ReferenceDocumentVersionEditView, self).form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            "reference_documents:details",
            args=[self.object.id],
        )
