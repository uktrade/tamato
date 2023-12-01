# Create your views here.
from datetime import date

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
                "date_published": date.today().strftime("%d %b %Y"),
                "regulation_id": "TBC",
                "geo_area_id": GeographicalArea.objects.get(area_id="AL").area_id,
            },
        ]
        return context


class ReferenceDocumentsDetailView(TemplateView):
    template_name = "reference_documents/detail.jinja"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        context["ref_doc"] = {
            "name": "The Albania Preferential Tariff",
            "version": 1.4,
            "date_published": date.today().strftime("%d %b %Y"),
            "regulation_id": "TBC",
            "geo_area_id": GeographicalArea.objects.get(area_id="AL").area_id,
            "measure_list": Measure.objects.filter(
                measure_type__sid="142",
                geographical_area__area_id="AL",
            )[:10],
        }
        return context
