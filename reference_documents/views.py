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
# Create your views here.
from datetime import date

from django.db.models import Q
from django.views.generic import TemplateView

from geo_areas.models import GeographicalArea
from measures.models import Measure


class ReferenceDocumentsListView(TemplateView):
    template_name = "reference_documents/list.jinja"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["object_list"] = [
            {
                "name": "The Albania Preferential Tariff",
                "version": 1.4,
                "date_published": date(2023, 4, 12).strftime("%d %b %Y"),
                "regulation_id": "TBC",
                "geo_area_id": GeographicalArea.objects.get(area_id="AL").area_id,
            },
        ]
        return context


class ReferenceDocumentsDetailView(TemplateView):
    template_name = "reference_documents/detail.jinja"

    def get_pref_duty_rates(self):
        """Returns a list of measures associated with the Albania Preferential
        Tariff."""
        # Measures with type 142, for Albania, Valid up to and including 12th April 2023

        date_filter_query = Q(valid_between__contains=date(2023, 4, 12)) | Q(
            valid_between__startswith__lt=date(2023, 4, 12),
        )
        pref_duty_measure_list = Measure.objects.filter(
            date_filter_query,
            measure_type__sid="142",
            geographical_area__area_id="AL",
        )[:20]

        return pref_duty_measure_list

    def get_tariff_quota_data(self):
        """Returns a dict of quota order numbers, and their linked definitions
        that are associated with the Albania Preferential Tariff."""
        # Measures with type 143, for Albania, with descriptions that are valid for 2023 only.

        # measures
        albanian_measures = (
            Measure.objects.filter(
                measure_type__sid="143",
                geographical_area__area_id="AL",
            )
            .exclude(order_number=None)
            .order_by("-valid_between")[:30]
        )

        # order_numbers of measures
        albanian_order_numbers = []
        for measure in albanian_measures:
            albanian_order_numbers.append(measure.order_number)

        # remove the duplicates
        albanian_order_numbers = list(dict.fromkeys(albanian_order_numbers))

        quotas = []

        for order_number in albanian_order_numbers:
            comm_codes = []
            for measure in albanian_measures:
                if measure.order_number == order_number:
                    comm_codes.append(measure.goods_nomenclature)

            quotas.append({"order_number": order_number, "comm_codes": comm_codes})

        # Get the current definition for each order number in the quotas list
        for quota in quotas:
            for definition in quota["order_number"].definitions.current():
                if definition.valid_between.upper.year == 2023:
                    quota["definition"] = definition
        return quotas

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        context["ref_doc"] = {
            "name": "The Albania Preferential Tariff",
            "version": 1.4,
            "date_published": date(2023, 4, 12).strftime("%d %b %Y"),
            "pref_duty_measure_list": self.get_pref_duty_rates(),
            "quotas": self.get_tariff_quota_data(),
        }
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
