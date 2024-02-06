from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import ListView

from geo_areas.models import GeographicalArea
from geo_areas.models import GeographicalAreaDescription
from reference_documents.models import ReferenceDocument


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
                        {"text": ""},
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
                        {"text": ""},
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
