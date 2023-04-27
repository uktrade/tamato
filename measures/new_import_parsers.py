from datetime import date

from importer.new_parsers import NewElementParser
from importer.parsers import NewValidityMixin
from importer.parsers import NewWritable


class NewMeasureTypeSeriesParser(NewValidityMixin, NewWritable, NewElementParser):
    record_code = "140"
    subrecord_code = "00"

    xml_object_tag = "measure.type.series"

    sid: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None
    measure_type_combination: str = None


class NewMeasureTypeSeriesDescriptionParser(NewWritable, NewElementParser):
    record_code = "140"
    subrecord_code = "05"

    xml_object_tag = "measure.type.series.description"

    sid: str = None
    language_id: str = None
    description: str = None


class NewMeasurementUnitParser(NewValidityMixin, NewWritable, NewElementParser):
    record_code = "210"
    subrecord_code = "00"

    xml_object_tag = "measurement.unit"

    code: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None


class NewMeasurementUnitDescriptionParser(NewWritable, NewElementParser):
    record_code = "210"
    subrecord_code = "05"

    xml_object_tag = "measurement.unit.description"

    code: str = None
    language_id: str = None
    description: str = None


class NewMeasurementUnitQualifierParser(
    NewValidityMixin,
    NewWritable,
    NewElementParser,
):
    record_code = "215"
    subrecord_code = "00"

    xml_object_tag = "measurement.unit.qualifier"

    code: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None


class NewMeasurementUnitQualifierDescriptionParser(NewWritable, NewElementParser):
    record_code = "215"
    subrecord_code = "05"

    xml_object_tag = "measurement.unit.qualifier.description"

    code: str = None
    language_id: str = None
    description: str = None


class NewMeasurementParser(NewValidityMixin, NewWritable, NewElementParser):
    record_code = "220"
    subrecord_code = "00"

    xml_object_tag = "measurement"

    measurement_unit__code: str = None
    measurement_unit_qualifier__code: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None


class NewMonetaryUnitParser(NewValidityMixin, NewWritable, NewElementParser):
    record_code = "225"
    subrecord_code = "00"

    xml_object_tag = "monetary.unit"

    code: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None


class NewMonetaryUnitDescriptionParser(NewWritable, NewElementParser):
    record_code = "225"
    subrecord_code = "05"

    xml_object_tag = "monetary.unit.description"

    code: str = None
    language_id: str = None
    description: str = None


class NewDutyExpressionParser(NewValidityMixin, NewWritable, NewElementParser):
    record_code = "230"
    subrecord_code = "00"

    xml_object_tag = "duty.expression"

    sid: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None
    duty_amount_applicability_code: date = None
    measurement_unit_applicability_code: date = None
    monetary_unit_applicability_code: date = None


class NewDutyExpressionDescriptionParser(NewWritable, NewElementParser):
    record_code = "230"
    subrecord_code = "05"

    xml_object_tag = "duty.expression.description"

    sid: str = None
    language_id: str = None
    description: str = None


class NewMeasureTypeParser(NewValidityMixin, NewWritable, NewElementParser):
    record_code = "235"
    subrecord_code = "00"

    xml_object_tag = "measure.type"

    sid: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None
    trade_movement_code: str = None
    priority_code: str = None
    measure_component_applicability_code: str = None
    origin_destination_code: str = None
    order_number_capture_code: str = None
    measure_explosion_level: str = None
    measure_type_series__sid: str = None


class NewMeasureTypeDescriptionParser(NewWritable, NewElementParser):
    record_code = "235"
    subrecord_code = "05"

    xml_object_tag = "measure.type.description"

    sid: str = None
    language_id: str = None
    description: str = None


class NewAdditionalCodeTypeMeasureTypeParser(
    NewValidityMixin,
    NewWritable,
    NewElementParser,
):
    record_code = "240"
    subrecord_code = "00"

    xml_object_tag = "additional.code.type.measure.type"

    measure_type__sid: str = None
    additional_code_type__sid: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None


class NewMeasureConditionCodeParser(NewValidityMixin, NewWritable, NewElementParser):
    record_code = "350"
    subrecord_code = "00"

    xml_object_tag = "measure.condition.code"

    code: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None


class NewMeasureConditionCodeDescriptionParser(NewWritable, NewElementParser):
    record_code = "350"
    subrecord_code = "05"

    xml_object_tag = "measure.condition.code.description"

    code: str = None
    language_id: str = None
    description: str = None


class NewMeasureActionParser(NewValidityMixin, NewWritable, NewElementParser):
    record_code = "355"
    subrecord_code = "00"

    xml_object_tag = "measure.action"

    code: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None


class NewMeasureActionDescriptionParser(NewWritable, NewElementParser):
    record_code = "355"
    subrecord_code = "05"

    xml_object_tag = "measure.action.description"

    code: str = None
    language_id: str = None
    description: str = None


class NewMeasureParser(NewValidityMixin, NewWritable, NewElementParser):
    record_code = "430"
    subrecord_code = "00"

    xml_object_tag = "measure"

    sid: str = None
    measure_type__sid: str = None
    geographical_area__area_id: str = None
    goods_nomenclature__item_id: str = None
    additional_code__type__sid: str = None
    additional_code__code: str = None
    order_number__order_number: str = None
    reduction: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None
    generating_regulation__role_type: str = None
    generating_regulation__regulation_id: str = None
    terminating_regulation__role_type: str = None
    terminating_regulation__regulation_id: str = None
    stopped: str = None
    geographical_area__sid: str = None
    goods_nomenclature__sid: str = None
    additional_code__sid: str = None


class NewMeasureComponentParser(NewWritable, NewElementParser):
    record_code = "430"
    subrecord_code = "05"

    xml_object_tag = "measure.component"

    component_measure__sid: str = None
    duty_expression__sid: str = None
    duty_amount: str = None
    monetary_unit__code: str = None
    component_measurement__measurement_unit__code: str = None
    component_measurement__measurement_unit_qualifier__code: str = None


class NewMeasureConditionParser(NewWritable, NewElementParser):
    record_code = "430"
    subrecord_code = "10"

    xml_object_tag = "measure.condition"

    sid: str = None
    dependent_measure__sid: str = None
    condition_code__code: str = None
    component_sequence_number: str = None
    duty_amount: str = None
    monetary_unit__code: str = None
    condition_measurement__measurement_unit__code: str = None
    condition_measurement__measurement_unit_qualifier__code: str = None
    action__code: str = None
    required_certificate__certificate_type__sid: str = None
    required_certificate__sid: str = None


class NewMeasureConditionComponentParser(NewWritable, NewElementParser):
    record_code = "430"
    subrecord_code = "11"

    xml_object_tag = "measure.condition.component"

    condition__sid: str = None
    duty_expression__sid: str = None
    duty_amount: str = None
    monetary_unit__code: str = None
    component_measurement__measurement_unit__code: str = None
    component_measurement__measurement_unit_qualifier__code: str = None


class NewMeasureExcludedGeographicalAreaParser(NewWritable, NewElementParser):
    record_code = "430"
    subrecord_code = "15"

    xml_object_tag = "measure.excluded.geographical.area"

    modified_measure__sid: str = None
    excluded_geographical_area__area_id: str = None
    excluded_geographical_area__sid: str = None


class NewFootnoteAssociationMeasureParser(NewWritable, NewElementParser):
    record_code = "430"
    subrecord_code = "20"

    xml_object_tag = "footnote.association.measure"

    footnoted_measure__sid: str = None
    associated_footnote__footnote_type__footnote_type_id: str = None
    associated_footnote__footnote_id: str = None
