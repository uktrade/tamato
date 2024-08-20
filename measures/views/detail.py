from itertools import groupby
from operator import attrgetter
from typing import Any

from common.views import TrackedModelDetailView
from measures import models
from measures.views.mixins import MeasureMixin


class MeasureDetail(MeasureMixin, TrackedModelDetailView):
    model = models.Measure
    template_name = "measures/detail.jinja"
    queryset = models.Measure.objects.latest_approved()

    def get_context_data(self, **kwargs: Any):
        conditions = (
            self.object.conditions.current()
            .prefetch_related(
                "condition_code",
                "required_certificate",
                "required_certificate__certificate_type",
                "condition_measurement__measurement_unit",
                "condition_measurement__measurement_unit_qualifier",
                "action",
            )
            .order_by("condition_code__code", "component_sequence_number")
        )
        condition_groups = groupby(conditions, attrgetter("condition_code"))

        context = super().get_context_data(**kwargs)
        context["condition_groups"] = condition_groups
        context["has_conditions"] = bool(len(conditions))
        return context
