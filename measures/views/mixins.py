from typing import Type

from common.models import TrackedModel
from measures import models
from workbaskets.forms import SelectableObjectsForm
from workbaskets.models import WorkBasket
from workbaskets.session_store import SessionStore


class MeasureMixin:
    model: Type[TrackedModel] = models.Measure

    def get_queryset(self):
        tx = WorkBasket.get_current_transaction(self.request)

        return models.Measure.objects.approved_up_to_transaction(tx)


class MeasureSessionStoreMixin:
    @property
    def session_store(self):
        return SessionStore(
            self.request,
            "MULTIPLE_MEASURE_SELECTIONS",
        )


class MeasureSelectionMixin(MeasureSessionStoreMixin):
    @property
    def measure_selections(self):
        """Get the IDs of measure that are candidates for editing/deletion."""
        return [
            SelectableObjectsForm.object_id_from_field_name(name)
            for name in [*self.session_store.data]
        ]

    @property
    def measure_selectors(self):
        """
        Used for JavaScript.

        Get the checkbox names of measure that are candidates for
        editing/deletion.
        """
        return list(self.session_store.data.keys())


class MeasureSelectionQuerysetMixin(MeasureSelectionMixin):
    def get_queryset(self):
        """Get the queryset for measures that are candidates for
        editing/deletion."""
        return models.Measure.objects.filter(pk__in=self.measure_selections)
