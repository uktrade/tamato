from django.views.generic import TemplateView

from measures import models
from workbaskets.models import WorkBasket


class DutySentenceReference(TemplateView):
    template_name = "duties/duty_sentence_guide.jinja"

    @property
    def tx(self):
        return WorkBasket.get_current_transaction(self.request)

    def measurements(self):
        return (
            models.Measurement.objects.approved_up_to_transaction(
                self.tx,
            )
            .select_related("measurement_unit", "measurement_unit_qualifier")
            .order_by("measurement_unit__code")
        )

    def measurement_units(self):
        return models.MeasurementUnit.objects.approved_up_to_transaction(
            self.tx,
        ).order_by("code")

    def measurement_unit_qualifiers(self):
        return models.MeasurementUnitQualifier.objects.approved_up_to_transaction(
            self.tx,
        ).order_by("code")

    def monetary_units(self):
        return models.MonetaryUnit.objects.approved_up_to_transaction(self.tx).order_by(
            "code",
        )

    def duty_expressions(self):
        return models.DutyExpression.objects.approved_up_to_transaction(
            self.tx,
        ).order_by("sid")

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            duty_expressions=self.duty_expressions(),
            measurements=self.measurements(),
            measurement_units=self.measurement_units(),
            measurement_unit_qualifiers=self.measurement_unit_qualifiers(),
            monetary_units=self.monetary_units(),
            **kwargs,
        )
