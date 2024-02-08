from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import DetailView
from django.views.generic import ListView

from geo_areas.models import GeographicalArea
from geo_areas.models import GeographicalAreaDescription
from reference_documents.models import ReferenceDocument
from reference_documents.models import ReferenceDocumentVersion


class ReferenceDocumentList(PermissionRequiredMixin, ListView):
    """UI endpoint for viewing and filtering workbaskets."""

    template_name = "reference_documents/index.jinja"
    permission_required = "reference_documents.view_reference_document"
    model = ReferenceDocument

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        reference_documents = []

        for reference in ReferenceDocument.objects.all().order_by("area_id"):
            if reference.reference_document_versions.count() == 0:
                reference_documents.append(
                    [
                        {"text": "None"},
                        {
                            "text": f"{reference.area_id} - ({self.get_name_by_area_id(reference.area_id)})",
                        },
                        {"text": 0},
                        {"text": 0},
                        {
                            "html": f'<a href="/reference_documents/{reference.id}">Details</a>',
                        },
                    ],
                )

            else:
                reference_documents.append(
                    [
                        {"text": reference.reference_document_versions.last().version},
                        {
                            "text": f"{reference.area_id} - ({self.get_name_by_area_id(reference.area_id)})",
                        },
                        {
                            "text": reference.reference_document_versions.last().preferential_rates.count(),
                        },
                        {
                            "text": reference.reference_document_versions.last().preferential_quotas.count(),
                        },
                        {
                            "html": f'<a href="/reference_documents/{reference.id}">Details</a>',
                        },
                    ],
                )

        context["reference_documents"] = reference_documents
        context["reference_document_headers"] = [
            {"text": "Latest Version"},
            {"text": "Country"},
            {"text": "Duties"},
            {"text": "Quotas"},
            {"text": "Actions"},
        ]
        return context

    def get_name_by_area_id(self, area_id):
        geo_area = (
            GeographicalArea.objects.latest_approved().filter(area_id=area_id).first()
        )
        if geo_area:
            geo_area_name = (
                GeographicalAreaDescription.objects.latest_approved()
                .filter(described_geographicalarea_id=geo_area.trackedmodel_ptr_id)
                .last()
            )
            return geo_area_name.description if geo_area_name else "None"
        return "None"


class ReferenceDocumentDetails(PermissionRequiredMixin, DetailView):
    template_name = "reference_documents/details.jinja"
    permission_required = "reference_documents.view_reference_document"
    model = ReferenceDocument

    def get_context_data(self, *args, **kwargs):
        context = super(ReferenceDocumentDetails, self).get_context_data(
            *args,
            **kwargs,
        )

        context["reference_document_versions_headers"] = [
            {"text": "Version"},
            {"text": "Duties"},
            {"text": "Quotas"},
            {"text": "Actions"},
        ]
        reference_document_versions = []

        print(self.request)

        for version in context["object"].reference_document_versions.order_by(
            "version",
        ):
            reference_document_versions.append(
                [
                    {
                        "text": version.version,
                    },
                    {
                        "text": version.preferential_rates.count(),
                    },
                    {
                        "text": version.preferential_quotas.count(),
                    },
                    {
                        "html": f'<a href="/reference_document_versions/{version.id}">version details</a>',
                    },
                ],
            )

        context["reference_document_versions"] = reference_document_versions

        return context


class ReferenceDocumentVersionDetails(PermissionRequiredMixin, DetailView):
    template_name = "reference_document_versions/details.jinja"
    permission_required = "reference_documents.view_reference_document"
    model = ReferenceDocumentVersion

    def get_context_data(self, *args, **kwargs):
        context = super(ReferenceDocumentVersionDetails, self).get_context_data(
            *args,
            **kwargs,
        )

        context["reference_document_version_duties_headers"] = [
            {"text": "Comm Code"},
            {"text": "Duty Rate"},
            {"text": "Validity"},
            {"text": "Actions"},
        ]

        context["reference_document_version_quotas_headers"] = [
            {"text": "Order Number"},
            {"text": "Comm Code"},
            {"text": "Rate"},
            {"text": "Volume"},
            {"text": "Validity"},
            {"text": "Actions"},
        ]

        reference_document_version_duties = []
        reference_document_version_quotas = []

        print(self.request)

        for duty in context["object"].preferential_rates.order_by("order"):
            validity = ""

            if duty.valid_start_day:
                validity = f"{duty.valid_start_day}/{duty.valid_start_month} - {duty.valid_end_day}/{duty.valid_end_month}"

            reference_document_version_duties.append(
                [
                    {
                        "text": duty.commodity_code,
                    },
                    {
                        "text": duty.duty_rate,
                    },
                    {
                        "text": validity,
                    },
                    {
                        "text": "",
                    },
                ],
            )

        for quota in context["object"].preferential_quotas.order_by("order"):
            validity = ""

            if quota.valid_start_day:
                validity = f"{quota.valid_start_day}/{quota.valid_start_month} - {quota.valid_end_day}/{quota.valid_end_month}"

            reference_document_version_quotas.append(
                [
                    {
                        "text": quota.quota_order_number,
                    },
                    {
                        "text": quota.commodity_code,
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
                        "text": "",
                    },
                ],
            )

        context["reference_document_version_duties"] = reference_document_version_duties

        context["reference_document_version_quotas"] = reference_document_version_quotas

        return context
