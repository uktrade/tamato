import logging

from importer.namespaces import Tag
from importer.parsers import ElementParser
from importer.parsers import TextElement
from importer.parsers import ValidityMixin
from importer.parsers import Writable
from importer.taric import Record
from measures import serializers


@Record.register_child("measure")
class Measure(Writable, ValidityMixin, ElementParser):
    serializer_class = serializers.MeasureSerializer

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
        serializer = serializers.MeasureSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        data.update(workbasket_id=workbasket_id)
        logging.debug(f"Creating Measure: {data}")
        serializer.create(data)


class MeasureComponent(Writable, ElementParser):
    tag = Tag("measure.component")
    measure_sid = TextElement(Tag("measure.sid"))
    duty_expression_sid = TextElement(Tag("duty.expression.sid"))
    duty_amount = TextElement(Tag("duty.amount"))
    monetary_unit_code = TextElement(Tag("monetary.unit.code"))
    measurement_unit_code = TextElement(Tag("measurement.unit.code"))


class MeasureCondition(Writable, ElementParser):
    tag = Tag("measure.condition")
    sid = TextElement(Tag("measure.condition.sid"))
    measure_sid = TextElement(Tag("measure.sid"))
    condition_code = TextElement(Tag("condition.code"))
    component_sequence_number = TextElement(Tag("component.sequence.number"))
    duty_amount = TextElement(Tag("condition.duty.amount"))
    monetary_unit_code = TextElement(Tag("condition.monetary.unit.code"))
    measurement_unit_code = TextElement(Tag("condition.measurement.unit.code"))
    action_code = TextElement(Tag("action.code"))


class MeasureConditionComponent(Writable, ElementParser):
    tag = Tag("measure.condition.component")
    measure_condition_sid = TextElement(Tag("measure.condition.sid"))
    duty_expression_sid = TextElement(Tag("duty.expression.sid"))
    duty_amount = TextElement(Tag("duty.amount"))
    monetary_unit_code = TextElement(Tag("monetary.unit.code"))
    measurement_unit_code = TextElement(Tag("measurement.unit.code"))


class MeasureExcludedGeographicalArea(Writable, ElementParser):
    tag = Tag("measure.excluded.geographical.area")
    measure_sid = TextElement(Tag("measure.sid"))
    excluded_geographical_area_sid = TextElement(Tag("excluded.geographical.area"))
    geographical_area_sid = TextElement(Tag("geograpical.area.sid"))
