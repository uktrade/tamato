from additional_codes.models import *
from certificates.models import *
from commodities.models import *
from footnotes.models import *
from geo_areas.models import *
from measures.models import *
from quotas.models import *
from regulations.models import *
from taric_parsers.parser_model_link import *
from taric_parsers.parsers.mixins import *
from taric_parsers.parsers.taric_parser import *


class NewMeasureTypeSeriesParser(ValidityMixin, Writable, BaseTaricParser):
    model = MeasureTypeSeries
    record_code = "140"
    subrecord_code = "00"

    xml_object_tag = "measure.type.series"

    model_links = []

    value_mapping = {
        "measure_type_series_id": "sid",
        "validity_start_date": "valid_between_lower",
        "validity_end_date": "valid_between_upper",
    }

    identity_fields = [
        "sid",
    ]

    allow_update_without_children = True

    sid: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None
    measure_type_combination: int = None


class NewMeasureTypeSeriesDescriptionParser(Writable, BaseTaricParser):
    model = MeasureTypeSeries
    parent_parser = NewMeasureTypeSeriesParser

    model_links = [
        ModelLink(
            MeasureTypeSeries,
            [ModelLinkField("sid", "sid")],
            "measure.type.series",
        ),
    ]

    value_mapping = {
        "measure_type_series_id": "sid",
    }

    record_code = "140"
    subrecord_code = "05"

    xml_object_tag = "measure.type.series.description"

    identity_fields = [
        "sid",
    ]

    deletes_allowed = False
    sid: str = None
    # language_id: str = None
    description: str = None


class NewMeasurementUnitParser(ValidityMixin, Writable, BaseTaricParser):
    # handler = MeasurementUnitHandler
    model = MeasurementUnit
    record_code = "210"
    subrecord_code = "00"

    xml_object_tag = "measurement.unit"

    identity_fields = [
        "code",
    ]

    value_mapping = {
        "measurement_unit_code": "code",
        "validity_start_date": "valid_between_lower",
        "validity_end_date": "valid_between_upper",
    }

    allow_update_without_children = True

    code: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None


class NewMeasurementUnitDescriptionParser(Writable, BaseTaricParser):
    model = MeasurementUnit
    parent_parser = NewMeasurementUnitParser

    model_links = [
        ModelLink(
            MeasurementUnit,
            [
                ModelLinkField("code", "code"),
            ],
            "measurement.unit",
        ),
    ]

    value_mapping = {
        "measurement_unit_code": "code",
    }

    record_code = "210"
    subrecord_code = "05"

    xml_object_tag = "measurement.unit.description"

    identity_fields = [
        "code",
    ]

    code: str = None
    # language_id: str = None
    description: str = None


class NewMeasurementUnitQualifierParser(
    ValidityMixin,
    Writable,
    BaseTaricParser,
):
    model = MeasurementUnitQualifier

    value_mapping = {
        "measurement_unit_qualifier_code": "code",
        "validity_start_date": "valid_between_lower",
        "validity_end_date": "valid_between_upper",
    }

    record_code = "215"
    subrecord_code = "00"

    xml_object_tag = "measurement.unit.qualifier"

    identity_fields = [
        "code",
    ]

    allow_update_without_children = True

    code: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None


class NewMeasurementUnitQualifierDescriptionParser(Writable, BaseTaricParser):
    model = MeasurementUnitQualifier
    parent_parser = NewMeasurementUnitQualifierParser

    model_links = [
        ModelLink(
            MeasurementUnitQualifier,
            [
                ModelLinkField("code", "code"),
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

    identity_fields = [
        "code",
    ]

    code: str = None
    # language_id: str = None
    description: str = None


class NewMeasurementParser(ValidityMixin, Writable, BaseTaricParser):
    model = Measurement

    model_links = [
        ModelLink(
            MeasurementUnit,
            [
                ModelLinkField("measurement_unit__code", "code"),
            ],
            "measurement.unit",
        ),
        ModelLink(
            MeasurementUnitQualifier,
            [
                ModelLinkField("measurement_unit_qualifier__code", "code"),
            ],
            "measurement.unit.qualifier",
        ),
    ]

    value_mapping = {
        "measurement_unit_code": "measurement_unit__code",
        "measurement_unit_qualifier_code": "measurement_unit_qualifier__code",
        "validity_start_date": "valid_between_lower",
        "validity_end_date": "valid_between_upper",
    }

    record_code = "220"
    subrecord_code = "00"

    xml_object_tag = "measurement"

    identity_fields = [
        "measurement_unit__code",
        "measurement_unit_qualifier__code",
    ]

    measurement_unit__code: str = None
    measurement_unit_qualifier__code: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None


class NewMonetaryUnitParser(ValidityMixin, Writable, BaseTaricParser):
    model = MonetaryUnit
    record_code = "225"
    subrecord_code = "00"

    xml_object_tag = "monetary.unit"

    model_links = []

    value_mapping = {
        "monetary_unit_code": "code",
        "validity_start_date": "valid_between_lower",
        "validity_end_date": "valid_between_upper",
    }

    identity_fields = [
        "code",
    ]

    allow_update_without_children = True

    code: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None


class NewMonetaryUnitDescriptionParser(Writable, BaseTaricParser):
    model = MonetaryUnit
    parent_parser = NewMonetaryUnitParser

    model_links = [
        ModelLink(
            MonetaryUnit,
            [
                ModelLinkField("code", "code"),
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

    identity_fields = [
        "code",
    ]

    code: str = None
    # language_id: str = None
    description: str = None


class NewDutyExpressionParser(ValidityMixin, Writable, BaseTaricParser):
    model = DutyExpression

    record_code = "230"
    subrecord_code = "00"

    xml_object_tag = "duty.expression"

    identity_fields = [
        "sid",
        "measurement_unit_applicability_code",
        "monetary_unit_applicability_code",
    ]

    model_links = []

    value_mapping = {
        "duty_expression_id": "sid",
        "validity_start_date": "valid_between_lower",
        "validity_end_date": "valid_between_upper",
    }

    allow_update_without_children = True

    sid: int = None
    valid_between_lower: date = None
    valid_between_upper: date = None
    duty_amount_applicability_code: int = None
    measurement_unit_applicability_code: int = None
    monetary_unit_applicability_code: int = None


class NewDutyExpressionDescriptionParser(Writable, BaseTaricParser):
    model = DutyExpression
    parent_parser = NewDutyExpressionParser

    model_links = [
        ModelLink(
            DutyExpression,
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

    identity_fields = [
        "sid",
    ]

    deletes_allowed = False
    sid: int = None
    # language_id: str = None
    description: str = None


class NewMeasureTypeParser(ValidityMixin, Writable, BaseTaricParser):
    # handler = MeasureTypeHandler
    model = MeasureType
    model_links = [
        ModelLink(
            MeasureTypeSeries,
            [
                ModelLinkField("measure_type_series__sid", "sid"),
            ],
            "measure.type.series",
        ),
    ]

    record_code = "235"
    subrecord_code = "00"

    xml_object_tag = "measure.type"

    value_mapping = {
        "measure_type_id": "sid",
        "measure_component_applicable_code": "measure_component_applicability_code",
        "origin_dest_code": "origin_destination_code",
        "measure_type_series_id": "measure_type_series__sid",
        "validity_start_date": "valid_between_lower",
        "validity_end_date": "valid_between_upper",
    }

    identity_fields = [
        "sid",
    ]

    allow_update_without_children = True

    sid: str = None
    trade_movement_code: int = None
    priority_code: int = None
    measure_component_applicability_code: int = None
    origin_destination_code: int = None
    order_number_capture_code: int = None
    measure_explosion_level: int = None
    measure_type_series__sid: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None


class NewMeasureTypeDescriptionParser(Writable, BaseTaricParser):
    model = MeasureType
    parent_parser = NewMeasureTypeParser

    model_links = [
        ModelLink(
            MeasureType,
            [
                ModelLinkField("sid", "sid"),
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

    identity_fields = [
        "sid",
    ]

    deletes_allowed = False
    sid: str = None
    # language_id: str = None
    description: str = None


class NewAdditionalCodeTypeMeasureTypeParser(
    ValidityMixin,
    Writable,
    BaseTaricParser,
):
    # handler = AdditionalCodeTypeMeasureTypeHandler
    model = AdditionalCodeTypeMeasureType
    model_links = [
        ModelLink(
            MeasureType,
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

    value_mapping = {
        "measure_type_id": "measure_type__sid",
        "additional_code_type_id": "additional_code_type__sid",
        "validity_start_date": "valid_between_lower",
        "validity_end_date": "valid_between_upper",
    }

    record_code = "240"
    subrecord_code = "00"

    xml_object_tag = "additional.code.type.measure.type"

    identity_fields = [
        "measure_type__sid",
        "additional_code_type__sid",
    ]

    measure_type__sid: str = None
    additional_code_type__sid: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None


class NewMeasureConditionCodeParser(ValidityMixin, Writable, BaseTaricParser):
    # handler = MeasureConditionCodeHandler
    model = MeasureConditionCode
    record_code = "350"
    subrecord_code = "00"

    xml_object_tag = "measure.condition.code"

    value_mapping = {
        "condition_code": "code",
        "validity_start_date": "valid_between_lower",
        "validity_end_date": "valid_between_upper",
    }

    identity_fields = [
        "code",
    ]

    allow_update_without_children = True

    code: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None


class NewMeasureConditionCodeDescriptionParser(Writable, BaseTaricParser):
    model = MeasureConditionCode
    parent_parser = NewMeasureConditionCodeParser

    model_links = [
        ModelLink(
            MeasureConditionCode,
            [
                ModelLinkField("code", "code"),
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

    identity_fields = [
        "code",
    ]

    deletes_allowed = False
    code: str = None
    # language_id: str = None
    description: str = None


class NewMeasureActionParser(ValidityMixin, Writable, BaseTaricParser):
    # handler = MeasureActionHandler
    model = MeasureAction

    model_links = []

    record_code = "355"
    subrecord_code = "00"

    xml_object_tag = "measure.action"

    value_mapping = {
        "action_code": "code",
        "validity_start_date": "valid_between_lower",
        "validity_end_date": "valid_between_upper",
    }

    identity_fields = [
        "code",
    ]

    allow_update_without_children = True

    code: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None


class NewMeasureActionDescriptionParser(Writable, BaseTaricParser):
    model = MeasureAction
    parent_parser = NewMeasureActionParser

    model_links = [
        ModelLink(
            MeasureAction,
            [
                ModelLinkField("code", "code"),
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

    identity_fields = [
        "code",
    ]

    deletes_allowed = False
    code: str = None
    # language_id: str = None
    description: str = None


class NewMeasureParser(ValidityMixin, Writable, BaseTaricParser):
    # handler = MeasureHandler
    model = Measure
    model_links = [
        ModelLink(
            MeasureType,
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
            AdditionalCode,
            [
                ModelLinkField("additional_code__code", "code"),
                ModelLinkField("additional_code__sid", "sid"),
                ModelLinkField("additional_code__type__sid", "type__sid"),
            ],
            "additional.code",
            True,
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

    value_mapping = {
        "measure_sid": "sid",
        "justification_regulation_role": "terminating_regulation__role_type",
        "justification_regulation_id": "terminating_regulation__regulation_id",
        "measure_type": "measure_type__sid",
        "geographical_area_sid": "geographical_area__sid",
        "geographical_area": "geographical_area__area_id",
        "goods_nomenclature_item_id": "goods_nomenclature__item_id",
        "additional_code_type": "additional_code__type__sid",
        "additional_code": "additional_code__code",
        "additional_code_sid": "additional_code__sid",
        "ordernumber": "order_number__order_number",
        "reduction_indicator": "reduction",
        "validity_start_date": "valid_between_lower",
        "validity_end_date": "valid_between_upper",
        "measure_generating_regulation_role": "generating_regulation__role_type",
        "measure_generating_regulation_id": "generating_regulation__regulation_id",
        "stopped_flag": "stopped",
        "goods_nomenclature_sid": "goods_nomenclature__sid",
    }

    record_code = "430"
    subrecord_code = "00"

    xml_object_tag = "measure"

    identity_fields = [
        "sid",
    ]

    sid: int = None
    measure_type__sid: str = None
    geographical_area__area_id: str = None
    geographical_area__sid: int = None
    goods_nomenclature__item_id: str = None
    goods_nomenclature__sid: int = None
    additional_code__type__sid: str = None
    additional_code__code: str = None
    additional_code__sid: int = None
    order_number__order_number: str = None
    reduction: int = None
    valid_between_lower: date = None
    valid_between_upper: date = None
    generating_regulation__role_type: int = None
    generating_regulation__regulation_id: str = None
    terminating_regulation__role_type: int = None
    terminating_regulation__regulation_id: str = None
    stopped: bool = None


class NewMeasureComponentParser(Writable, BaseTaricParser):
    # handler = MeasureComponentHandler
    model = MeasureComponent
    model_links = [
        ModelLink(
            Measure,
            [
                ModelLinkField("component_measure__sid", "sid"),
            ],
            "measure",
        ),
        ModelLink(
            DutyExpression,
            [
                ModelLinkField("duty_expression__sid", "sid"),
            ],
            "duty.expression",
        ),
        ModelLink(
            MonetaryUnit,
            [
                ModelLinkField("monetary_unit__code", "code"),
            ],
            "monetary.unit",
            True,
        ),
        ModelLink(
            Measurement,
            [
                ModelLinkField(
                    "component_measurement__measurement_unit__code",
                    "measurement_unit__code",
                ),
                ModelLinkField(
                    "component_measurement__measurement_unit_qualifier__code",
                    "measurement_unit_qualifier__code",
                ),
            ],
            "measurement",
            True,
        ),
    ]

    value_mapping = {
        "measure_sid": "component_measure__sid",
        "duty_expression_id": "duty_expression__sid",
        "monetary_unit_code": "monetary_unit__code",
        "measurement_unit_code": "component_measurement__measurement_unit__code",
        "measurement_unit_qualifier_code": "component_measurement__measurement_unit_qualifier__code",
    }

    record_code = "430"
    subrecord_code = "05"

    xml_object_tag = "measure.component"

    identity_fields = [
        "component_measure__sid",
        "component_measurement__measurement_unit__code",
        "component_measurement__measurement_unit_qualifier__code",
    ]

    component_measure__sid: int = None
    duty_expression__sid: int = None
    duty_amount: float = None
    monetary_unit__code: str = None
    component_measurement__measurement_unit__code: str = None
    component_measurement__measurement_unit_qualifier__code: str = None


class NewMeasureConditionParser(Writable, BaseTaricParser):
    # handler = MeasureConditionHandler
    model = MeasureCondition
    model_links = [
        ModelLink(
            Measure,
            [
                ModelLinkField("dependent_measure__sid", "sid"),
            ],
            "measure",
        ),
        ModelLink(
            MeasureConditionCode,
            [
                ModelLinkField("condition_code__code", "code"),
            ],
            "measure.condition.code",
        ),
        ModelLink(
            MonetaryUnit,
            [
                ModelLinkField("monetary_unit__code", "code"),
            ],
            "monetary.unit",
        ),
        ModelLink(
            Measurement,
            [
                ModelLinkField(
                    "condition_measurement__measurement_unit__code",
                    "measurement_unit__code",
                ),
                ModelLinkField(
                    "condition_measurement__measurement_unit_qualifier__code",
                    "measurement_unit_qualifier__code",
                ),
            ],
            "measurement",
        ),
        ModelLink(
            MeasureAction,
            [
                ModelLinkField("action__code", "code"),
            ],
            "measure.action",
        ),
        ModelLink(
            Certificate,
            [
                ModelLinkField("required_certificate__sid", "sid"),
                ModelLinkField(
                    "required_certificate__certificate_type__sid",
                    "certificate_type__sid",
                ),
            ],
            "certificate",
        ),
    ]

    record_code = "430"
    subrecord_code = "10"

    xml_object_tag = "measure.condition"

    value_mapping = {
        "measure_condition_sid": "sid",
        "measure_sid": "dependent_measure__sid",
        "condition_code": "condition_code__code",
        "condition_duty_amount": "duty_amount",
        "condition_monetary_unit_code": "monetary_unit__code",
        "condition_measurement_unit_code": "condition_measurement__measurement_unit__code",
        "condition_measurement_unit_qualifier_code": "condition_measurement__measurement_unit_qualifier__code",
        "action_code": "action__code",
        "certificate_type_code": "required_certificate__certificate_type__sid",
        "certificate_code": "required_certificate__sid",
    }

    identity_fields = [
        "sid",
    ]

    sid: int = None
    dependent_measure__sid: int = None
    condition_code__code: str = None
    component_sequence_number: int = None
    duty_amount: float = None
    monetary_unit__code: str = None
    condition_measurement__measurement_unit__code: str = None
    condition_measurement__measurement_unit_qualifier__code: str = None
    action__code: str = None
    required_certificate__certificate_type__sid: str = None
    required_certificate__sid: str = None


class NewMeasureConditionComponentParser(Writable, BaseTaricParser):
    # handler = MeasureConditionComponentHandler
    model = MeasureConditionComponent
    model_links = [
        ModelLink(
            MeasureCondition,
            [
                ModelLinkField("condition__sid", "sid"),
            ],
            "measure.condition",
        ),
        ModelLink(
            DutyExpression,
            [
                ModelLinkField("duty_expression__sid", "sid"),
            ],
            "duty.expression",
        ),
        ModelLink(
            MonetaryUnit,
            [
                ModelLinkField("monetary_unit__code", "code"),
            ],
            "monetary.unit",
        ),
        ModelLink(
            Measurement,
            [
                ModelLinkField(
                    "component_measurement__measurement_unit__code",
                    "measurement_unit__code",
                ),
                ModelLinkField(
                    "component_measurement__measurement_unit_qualifier__code",
                    "measurement_unit_qualifier__code",
                ),
            ],
            "measurement",
        ),
    ]

    record_code = "430"
    subrecord_code = "11"

    xml_object_tag = "measure.condition.component"

    value_mapping = {
        "measure_condition_sid": "condition__sid",
        "duty_expression_id": "duty_expression__sid",
        "monetary_unit_code": "monetary_unit__code",
        "measurement_unit_code": "component_measurement__measurement_unit__code",
        "measurement_unit_qualifier_code": "component_measurement__measurement_unit_qualifier__code",
    }

    identity_fields = [
        "condition__sid",
        "component_measurement__measurement_unit__code",
        "component_measurement__measurement_unit_qualifier__code",
    ]

    condition__sid: int = None
    duty_expression__sid: int = None
    duty_amount: float = None
    monetary_unit__code: str = None
    component_measurement__measurement_unit__code: str = None
    component_measurement__measurement_unit_qualifier__code: str = None


class NewMeasureExcludedGeographicalAreaParser(Writable, BaseTaricParser):
    # handler = MeasureExcludedGeographicalAreaHandler
    model = MeasureExcludedGeographicalArea
    model_links = [
        ModelLink(
            Measure,
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

    value_mapping = {
        "measure_sid": "modified_measure__sid",
        "excluded_geographical_area": "excluded_geographical_area__area_id",
        "geographical_area_sid": "excluded_geographical_area__sid",
    }

    identity_fields = [
        "modified_measure__sid",
        "excluded_geographical_area__sid",
    ]

    modified_measure__sid: int = None
    excluded_geographical_area__area_id: str = None
    excluded_geographical_area__sid: int = None


class NewFootnoteAssociationMeasureParser(Writable, BaseTaricParser):
    # handler = FootnoteAssociationMeasureHandler
    model = FootnoteAssociationMeasure
    model_links = [
        ModelLink(
            Measure,
            [
                ModelLinkField("footnoted_measure__sid", "sid"),
            ],
            "measure",
        ),
        ModelLink(
            Footnote,
            [
                ModelLinkField("associated_footnote__footnote_id", "footnote_id"),
                ModelLinkField(
                    "associated_footnote__footnote_type__footnote_type_id",
                    "footnote_type__footnote_type_id",
                ),
            ],
            "footnote",
        ),
    ]

    value_mapping = {
        "measure_sid": "footnoted_measure__sid",
        "footnote_type_id": "associated_footnote__footnote_type__footnote_type_id",
        "footnote_id": "associated_footnote__footnote_id",
    }

    record_code = "430"
    subrecord_code = "20"

    xml_object_tag = "footnote.association.measure"

    identity_fields = [
        "footnoted_measure__sid",
        "associated_footnote__footnote_id",
    ]

    updates_allowed = False

    footnoted_measure__sid: int = None
    associated_footnote__footnote_type__footnote_type_id: str = None
    associated_footnote__footnote_id: str = None
