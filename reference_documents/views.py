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
