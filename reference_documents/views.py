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
