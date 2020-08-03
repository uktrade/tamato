import logging

from importer.taric import Record
from measures.serializers import MeasureSerializer

from importer.handlers import ElementHandler
from importer.handlers import TextElement
from importer.handlers import ValidityMixin
from importer.handlers import Writable
from importer.namespaces import Tag


@Record.register_child("measure")
class Measure(Writable, ValidityMixin, ElementHandler):
    tag = Tag("measure")
    sid = TextElement(Tag("measure.sid"))
    measure_type = TextElement(Tag("measure.type"))
    geographical_area = TextElement(Tag("geographical.area"))
    commodity_code = TextElement(Tag("goods.nomenclature.item.id"))
    stopped = TextElement(Tag("stopped.flag"))
    valid_between_lower = TextElement(Tag("validity.start.date"))
    valid_between_upper = TextElement(Tag("validity.end.date"))

    def clean(self):
        super().clean()

        commodity_code = self.data.pop("commodity_code", None)
        if commodity_code:
            self.data["commodity_code"] = {
                "code": commodity_code,
            }

    def create(self, data, workbasket_id):
        serializer = MeasureSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        data.update(workbasket_id=workbasket_id)
        logging.debug(f"Creating Measure: {data}")
        serializer.create(data)


class MeasureComponent(Writable, ElementHandler):
    tag = Tag("measure.component")
    measure_sid = TextElement(Tag("measure.sid"))
    duty_expression_sid = TextElement(Tag("duty.expression.sid"))
    duty_amount = TextElement(Tag("duty.amount"))
    monetary_unit_code = TextElement(Tag("monetary.unit.code"))
    measurement_unit_code = TextElement(Tag("measurement.unit.code"))


class MeasureCondition(Writable, ElementHandler):
    tag = Tag("measure.condition")
    sid = TextElement(Tag("measure.condition.sid"))
    measure_sid = TextElement(Tag("measure.sid"))
    condition_code = TextElement(Tag("condition.code"))
    component_sequence_number = TextElement(Tag("component.sequence.number"))
    duty_amount = TextElement(Tag("condition.duty.amount"))
    monetary_unit_code = TextElement(Tag("condition.monetary.unit.code"))
    measurement_unit_code = TextElement(Tag("condition.measurement.unit.code"))
    action_code = TextElement(Tag("action.code"))


class MeasureConditionComponent(Writable, ElementHandler):
    tag = Tag("measure.condition.component")
    measure_condition_sid = TextElement(Tag("measure.condition.sid"))
    duty_expression_sid = TextElement(Tag("duty.expression.sid"))
    duty_amount = TextElement(Tag("duty.amount"))
    monetary_unit_code = TextElement(Tag("monetary.unit.code"))
    measurement_unit_code = TextElement(Tag("measurement.unit.code"))


class MeasureExcludedGeographicalArea(Writable, ElementHandler):
    tag = Tag("measure.excluded.geographical.area")
    measure_sid = TextElement(Tag("measure.sid"))
    excluded_geographical_area_sid = TextElement(Tag("excluded.geographical.area"))
    geographical_area_sid = TextElement(Tag("geograpical.area.sid"))
