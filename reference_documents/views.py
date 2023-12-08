# Create your views here.
from datetime import date

from django.db.models import Q
from django.views.generic import TemplateView

from geo_areas.models import GeographicalArea
from measures.models import Measure
from quotas.models import QuotaDefinition


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

    def get_quota_data(self):
        # Get all the order numbers from measures with type 143, and location of Albania
        quotas = []
        for measure in Measure.objects.filter(
            measure_type__sid="143",
            geographical_area__area_id="AL",
        ).exclude(order_number=None)[:20]:
            quotas.append(measure.order_number)

        # For each order number..
        current_definitions = []
        for order_number in quotas:
            for definition in QuotaDefinition.objects.filter(
                valid_between__contains=date.today(),
                order_number=order_number,
            ):
                current_definitions.append(
                    {
                        "order_number": order_number,
                        "definition_start_date": definition.valid_between.lower.year,
                        "definition_end_date": definition.valid_between.upper.year,
                    },
                )
        return current_definitions

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        date_filter_query = Q(valid_between__contains=date(2023, 4, 12)) | Q(
            valid_between__startswith__lt=date(2023, 4, 12),
        )

        measure_list = Measure.objects.filter(
            date_filter_query,
            measure_type__sid="142",
            geographical_area__area_id="AL",
        )[:20]

        context["ref_doc"] = {
            "name": "The Albania Preferential Tariff",
            "version": 1.4,
            "date_published": date(2023, 4, 12).strftime("%d %b %Y"),
            "regulation_id": "TBC",
            "geo_area_id": GeographicalArea.objects.get(area_id="AL").area_id,
            "measure_list": measure_list,
            "quotas": self.get_quota_data(),
        }
        return context
