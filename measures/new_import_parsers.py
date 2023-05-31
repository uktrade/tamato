from datetime import date

from certificates.models import CertificateType
from footnotes.models import FootnoteType
from importer.new_parsers import ModelLink
from importer.new_parsers import ModelLinkField
from importer.new_parsers import NewElementParser
from importer.parsers import NewValidityMixin
from importer.parsers import NewWritable
from measures.import_handlers import *


class NewMeasureTypeSeriesParser(NewValidityMixin, NewWritable, NewElementParser):
    model = models.MeasureTypeSeries
    record_code = "140"
    subrecord_code = "00"

    xml_object_tag = "measure.type.series"

    sid: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None
    measure_type_combination: str = None


class NewMeasureTypeSeriesDescriptionParser(NewWritable, NewElementParser):
    model = models.MeasureTypeSeries
    parent_parser = NewMeasureTypeSeriesParser

    model_links = [
        ModelLink(
            models.MeasureTypeSeries,
            [
                ModelLinkField("measure_type_series__id", "sid"),
            ],
            "measure.type.series",
        ),
    ]

    value_mapping = {
        "measure_type_series__id": "sid",
    }

    record_code = "140"
    subrecord_code = "05"

    xml_object_tag = "measure.type.series.description"

    sid: str = None
    # language_id: str = None
    description: str = None


class NewMeasurementUnitParser(NewValidityMixin, NewWritable, NewElementParser):
    # handler = MeasurementUnitHandler
    model = models.MeasurementUnit
    record_code = "210"
    subrecord_code = "00"

    xml_object_tag = "measurement.unit"

    code: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None


class NewMeasurementUnitDescriptionParser(NewWritable, NewElementParser):
    model = models.MeasurementUnit
    parent_parser = NewMeasurementUnitParser

    model_links = [
        ModelLink(
            models.MeasurementUnit,
            [
                ModelLinkField("measurement_unit__code", "code"),
            ],
            "measurement.unit",
        ),
    ]

    value_mapping = {
        "measurement_unit__code": "code",
    }

    record_code = "210"
    subrecord_code = "05"

    xml_object_tag = "measurement.unit.description"

    code: str = None
    # language_id: str = None
    description: str = None


class NewMeasurementUnitQualifierParser(
    NewValidityMixin,
    NewWritable,
    NewElementParser,
):
    model = models.MeasurementUnitQualifier

    value_mapping = {
        "measurement_unit_qualifier_code": "code",
    }

    record_code = "215"
    subrecord_code = "00"

    xml_object_tag = "measurement.unit.qualifier"

    code: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None


class NewMeasurementUnitQualifierDescriptionParser(NewWritable, NewElementParser):
    model = models.MeasurementUnitQualifier
    parent_parser = NewMeasurementUnitQualifierParser

    model_links = [
        ModelLink(
            models.MeasurementUnitQualifier,
            [
                ModelLinkField("measurement_unit__code", "code"),
            ],
            "measurement.unit.qualifier",
        ),
    ]

    value_mapping = {
        "measurement_unit_qualifier_code": "code",
    }

    record_code = "215"
    subrecord_code = "05"

    xml_object_tag = "measurement.unit.qualifier.description"

    code: str = None
    # language_id: str = None
    description: str = None


class NewMeasurementParser(NewValidityMixin, NewWritable, NewElementParser):
    model = models.Measurement

    model_links = [
        ModelLink(
            models.MeasurementUnit,
            [
                ModelLinkField("measurement_unit__code", "code"),
            ],
            "measurement.unit",
        ),
        ModelLink(
            models.MeasurementUnitQualifier,
            [
                ModelLinkField("measurement_unit_qualifier__code", "code"),
            ],
            "measurement.unit.qualifier",
        ),
    ]

    record_code = "220"
    subrecord_code = "00"

    xml_object_tag = "measurement"

    measurement_unit__code: str = None
    measurement_unit_qualifier__code: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None


class NewMonetaryUnitParser(NewValidityMixin, NewWritable, NewElementParser):
    model = models.MonetaryUnit
    record_code = "225"
    subrecord_code = "00"

    xml_object_tag = "monetary.unit"

    code: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None


class NewMonetaryUnitDescriptionParser(NewWritable, NewElementParser):
    model = models.MonetaryUnit
    parent_parser = NewMonetaryUnitParser

    model_links = [
        ModelLink(
            models.MonetaryUnit,
            [
                ModelLinkField("monetary_unit__code", "code"),
            ],
            "monetary.unit",
        ),
    ]

    value_mapping = {
        "monetary_unit_code": "code",
    }

    record_code = "225"
    subrecord_code = "05"

    xml_object_tag = "monetary.unit.description"

    code: str = None
    # language_id: str = None
    description: str = None


class NewDutyExpressionParser(NewValidityMixin, NewWritable, NewElementParser):
    model = models.DutyExpression

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
    model = models.DutyExpression
    parent_parser = NewDutyExpressionParser

    model_links = [
        ModelLink(
            models.DutyExpression,
            [
                ModelLinkField("sid", "sid"),
            ],
            "duty.expression",
        ),
    ]

    value_mapping = {
        "duty_expression_id": "sid",
    }

    record_code = "230"
    subrecord_code = "05"

    xml_object_tag = "duty.expression.description"

    sid: str = None
    # language_id: str = None
    description: str = None


class NewMeasureTypeParser(NewValidityMixin, NewWritable, NewElementParser):
    # handler = MeasureTypeHandler
    model = models.MeasureType
    model_links = [
        ModelLink(
            models.MeasureTypeSeries,
            [
                ModelLinkField("measure_type_series__sid", "sid"),
            ],
            "measure.type.series",
        ),
    ]

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
    model = models.MeasureType
    parent_parser = NewMeasureTypeParser

    model_links = [
        ModelLink(
            models.MeasureType,
            [
                ModelLinkField("measure_type__sid", "sid"),
            ],
            "measure.type",
        ),
    ]

    value_mapping = {
        "measure_type_id": "sid",
    }

    record_code = "235"
    subrecord_code = "05"

    xml_object_tag = "measure.type.description"

    sid: str = None
    # language_id: str = None
    description: str = None


class NewAdditionalCodeTypeMeasureTypeParser(
    NewValidityMixin,
    NewWritable,
    NewElementParser,
):
    # handler = AdditionalCodeTypeMeasureTypeHandler
    model = models.AdditionalCodeTypeMeasureType
    model_links = [
        ModelLink(
            models.MeasureType,
            [
                ModelLinkField("measure_type__sid", "sid"),
            ],
            "measure.type",
        ),
        ModelLink(
            AdditionalCodeType,
            [
                ModelLinkField("additional_code_type__sid", "sid"),
            ],
            "additional.code.type",
        ),
    ]

    record_code = "240"
    subrecord_code = "00"

    xml_object_tag = "additional.code.type.measure.type"

    measure_type__sid: str = None
    additional_code_type__sid: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None


class NewMeasureConditionCodeParser(NewValidityMixin, NewWritable, NewElementParser):
    # handler = MeasureConditionCodeHandler
    model = models.MeasureConditionCode
    record_code = "350"
    subrecord_code = "00"

    xml_object_tag = "measure.condition.code"

    code: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None


class NewMeasureConditionCodeDescriptionParser(NewWritable, NewElementParser):
    model = models.MeasureConditionCode
    parent_parser = NewMeasureConditionCodeParser

    model_links = [
        ModelLink(
            models.MeasureConditionCode,
            [
                ModelLinkField("condition_code", "code"),
            ],
            "measure.condition.code",
        ),
    ]

    value_mapping = {
        "condition_code": "code",
    }

    record_code = "350"
    subrecord_code = "05"

    xml_object_tag = "measure.condition.code.description"

    code: str = None
    # language_id: str = None
    description: str = None


class NewMeasureActionParser(NewValidityMixin, NewWritable, NewElementParser):
    # handler = MeasureActionHandler
    model = models.MeasureAction
    record_code = "355"
    subrecord_code = "00"

    xml_object_tag = "measure.action"

    code: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None


class NewMeasureActionDescriptionParser(NewWritable, NewElementParser):
    model = models.MeasureAction
    parent_parser = NewMeasureActionParser

    model_links = [
        ModelLink(
            models.MeasureAction,
            [
                ModelLinkField("action_code", "code"),
            ],
            "measure.action",
        ),
    ]

    value_mapping = {
        "action_code": "code",
    }
    record_code = "355"
    subrecord_code = "05"

    xml_object_tag = "measure.action.description"

    code: str = None
    # language_id: str = None
    description: str = None


class NewMeasureParser(NewValidityMixin, NewWritable, NewElementParser):
    # handler = MeasureHandler
    model = models.Measure
    model_links = [
        ModelLink(
            models.MeasureType,
            [
                ModelLinkField("measure_type__sid", "sid"),
            ],
            "measure.type",
        ),
        ModelLink(
            GeographicalArea,
            [
                ModelLinkField("geographical_area__area_id", "area_id"),
                ModelLinkField("geographical_area__sid", "sid"),
            ],
            "geographical.area",
        ),
        ModelLink(
            GoodsNomenclature,
            [
                ModelLinkField("goods_nomenclature__item_id", "item_id"),
                ModelLinkField("goods_nomenclature__sid", "sid"),
            ],
            "goods.nomenclature",
        ),
        ModelLink(
            AdditionalCodeType,
            [
                ModelLinkField("additional_code__type__sid", "sid"),
            ],
            "additional.code.type",
        ),
        ModelLink(
            AdditionalCode,
            [
                ModelLinkField("additional_code__code", "code"),
                ModelLinkField("additional_code__sid", "sid"),
            ],
            "additional.code",
        ),
        ModelLink(
            QuotaOrderNumber,
            [
                ModelLinkField("order_number__order_number", "order_number"),
            ],
            "additional.code.type",
            True,  # optional - can be blank
        ),
        ModelLink(
            Regulation,
            [
                ModelLinkField("generating_regulation__role_type", "role_type"),
                ModelLinkField("generating_regulation__regulation_id", "regulation_id"),
            ],
            "regulation",
        ),
        ModelLink(
            Regulation,
            [
                ModelLinkField("terminating_regulation__role_type", "role_type"),
                ModelLinkField(
                    "terminating_regulation__regulation_id",
                    "regulation_id",
                ),
            ],
            "regulation",
        ),
    ]

    record_code = "430"
    subrecord_code = "00"

    xml_object_tag = "measure"

    sid: str = None
    measure_type__sid: str = None
    geographical_area__area_id: str = None
    geographical_area__sid: str = None
    goods_nomenclature__item_id: str = None
    goods_nomenclature__sid: str = None
    additional_code__type__sid: str = None
    additional_code__code: str = None
    additional_code__sid: str = None
    order_number__order_number: str = None
    reduction: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None
    generating_regulation__role_type: str = None
    generating_regulation__regulation_id: str = None
    terminating_regulation__role_type: str = None
    terminating_regulation__regulation_id: str = None
    stopped: str = None


class NewMeasureComponentParser(NewWritable, NewElementParser):
    # handler = MeasureComponentHandler
    model = models.MeasureComponent
    model_links = [
        ModelLink(
            models.Measure,
            [
                ModelLinkField("component_measure__sid", "sid"),
            ],
            "measure",
        ),
        ModelLink(
            models.DutyExpression,
            [
                ModelLinkField("duty_expression__sid", "sid"),
            ],
            "duty.expression",
        ),
        ModelLink(
            models.MonetaryUnit,
            [
                ModelLinkField("monetary_unit__code", "code"),
            ],
            "monetary.unit",
        ),
        ModelLink(
            models.MeasurementUnit,
            [
                ModelLinkField("component_measurement__measurement_unit__code", "code"),
            ],
            "measurement.unit",
        ),
        ModelLink(
            models.MeasurementUnitQualifier,
            [
                ModelLinkField(
                    "component_measurement__measurement_unit_qualifier__code",
                    "code",
                ),
            ],
            "measurement.unit.qualifier",
        ),
    ]

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
    # handler = MeasureConditionHandler
    model = models.MeasureCondition
    model_links = [
        ModelLink(
            models.Measure,
            [
                ModelLinkField("dependent_measure__sid", "sid"),
            ],
            "measure",
        ),
        ModelLink(
            models.MeasureConditionCode,
            [
                ModelLinkField("condition_code__code", "code"),
            ],
            "measure.condition.code",
        ),
        ModelLink(
            models.MonetaryUnit,
            [
                ModelLinkField("monetary_unit__code", "code"),
            ],
            "monetary.unit",
        ),
        ModelLink(
            models.MeasurementUnit,
            [
                ModelLinkField("condition_measurement__measurement_unit__code", "code"),
            ],
            "measurement.unit",
        ),
        ModelLink(
            models.MeasurementUnitQualifier,
            [
                ModelLinkField(
                    "condition_measurement__measurement_unit_qualifier__code",
                    "code",
                ),
            ],
            "measurement.unit.qualifier",
        ),
        ModelLink(
            models.MeasureAction,
            [
                ModelLinkField("action__code", "code"),
            ],
            "measure.action",
        ),
        ModelLink(
            Certificate,
            [
                ModelLinkField("required_certificate__sid", "sid"),
            ],
            "certificate",
        ),
        ModelLink(
            CertificateType,
            [
                ModelLinkField("required_certificate__certificate_type__sid", "sid"),
            ],
            "certificate.type",
        ),
    ]

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
    # handler = MeasureConditionComponentHandler
    model = models.MeasureConditionComponent
    model_links = [
        ModelLink(
            models.MeasureCondition,
            [
                ModelLinkField("condition__sid", "sid"),
            ],
            "measure.condition",
        ),
        ModelLink(
            models.DutyExpression,
            [
                ModelLinkField("duty_expression__sid", "sid"),
            ],
            "duty.expression",
        ),
        ModelLink(
            models.MonetaryUnit,
            [
                ModelLinkField("monetary_unit__code", "code"),
            ],
            "monetary.unit",
        ),
        ModelLink(
            models.MeasurementUnit,
            [
                ModelLinkField("component_measurement__measurement_unit__code", "code"),
            ],
            "measurement.unit",
        ),
        ModelLink(
            models.MeasurementUnitQualifier,
            [
                ModelLinkField(
                    "component_measurement__measurement_unit_qualifier__code",
                    "code",
                ),
            ],
            "measurement.unit.qualifier",
        ),
    ]

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
    # handler = MeasureExcludedGeographicalAreaHandler
    model = models.MeasureExcludedGeographicalArea
    model_links = [
        ModelLink(
            models.Measure,
            [
                ModelLinkField("modified_measure__sid", "sid"),
            ],
            "measure",
        ),
        ModelLink(
            GeographicalArea,
            [
                ModelLinkField("excluded_geographical_area__area_id", "area_id"),
                ModelLinkField("excluded_geographical_area__sid", "sid"),
            ],
            "geographical.area",
        ),
    ]

    record_code = "430"
    subrecord_code = "15"

    xml_object_tag = "measure.excluded.geographical.area"

    modified_measure__sid: str = None
    excluded_geographical_area__area_id: str = None
    excluded_geographical_area__sid: str = None


class NewFootnoteAssociationMeasureParser(NewWritable, NewElementParser):
    # handler = FootnoteAssociationMeasureHandler
    model = models.FootnoteAssociationMeasure
    model_links = [
        ModelLink(
            models.Measure,
            [
                ModelLinkField("modified_measure__sid", "sid"),
            ],
            "measure",
        ),
        ModelLink(
            FootnoteType,
            [
                ModelLinkField(
                    "associated_footnote__footnote_type__footnote_type_id",
                    "footnote_type_id",
                ),
            ],
            "footnote.type",
        ),
        ModelLink(
            Footnote,
            [
                ModelLinkField("associated_footnote__footnote_id", "footnote_id"),
            ],
            "footnote",
        ),
    ]

    record_code = "430"
    subrecord_code = "20"

    xml_object_tag = "footnote.association.measure"

    footnoted_measure__sid: str = None
    associated_footnote__footnote_type__footnote_type_id: str = None
    associated_footnote__footnote_id: str = None
