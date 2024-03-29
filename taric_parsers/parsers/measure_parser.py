from datetime import date

from additional_codes.models import AdditionalCode
from additional_codes.models import AdditionalCodeType
from certificates.models import Certificate
from commodities.models import GoodsNomenclature
from footnotes.models import Footnote
from geo_areas.models import GeographicalArea
from measures.models import AdditionalCodeTypeMeasureType
from measures.models import DutyExpression
from measures.models import FootnoteAssociationMeasure
from measures.models import Measure
from measures.models import MeasureAction
from measures.models import MeasureComponent
from measures.models import MeasureCondition
from measures.models import MeasureConditionCode
from measures.models import MeasureConditionComponent
from measures.models import MeasureExcludedGeographicalArea
from measures.models import Measurement
from measures.models import MeasurementUnit
from measures.models import MeasurementUnitQualifier
from measures.models import MeasureType
from measures.models import MeasureTypeSeries
from measures.models import MonetaryUnit
from quotas.models import QuotaOrderNumber
from regulations.models import Regulation
from taric_parsers.parser_model_link import ModelLink
from taric_parsers.parser_model_link import ModelLinkField
from taric_parsers.parsers.mixins import ValidityMixin
from taric_parsers.parsers.mixins import Writable
from taric_parsers.parsers.taric_parser import BaseTaricParser


class MeasureTypeSeriesParserV2(ValidityMixin, Writable, BaseTaricParser):
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


class MeasureTypeSeriesDescriptionParserV2(Writable, BaseTaricParser):
    model = MeasureTypeSeries
    parent_parser = MeasureTypeSeriesParserV2

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
    description: str = None


class MeasurementUnitParserV2(ValidityMixin, Writable, BaseTaricParser):
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


class MeasurementUnitDescriptionParserV2(Writable, BaseTaricParser):
    model = MeasurementUnit
    parent_parser = MeasurementUnitParserV2

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
    description: str = None


class MeasurementUnitQualifierParserV2(
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


class MeasurementUnitQualifierDescriptionParserV2(Writable, BaseTaricParser):
    model = MeasurementUnitQualifier
    parent_parser = MeasurementUnitQualifierParserV2

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

    deletes_allowed = False
    code: str = None
    description: str = None


class MeasurementParserV2(ValidityMixin, Writable, BaseTaricParser):
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


class MonetaryUnitParserV2(ValidityMixin, Writable, BaseTaricParser):
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


class MonetaryUnitDescriptionParserV2(Writable, BaseTaricParser):
    model = MonetaryUnit
    parent_parser = MonetaryUnitParserV2

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

    deletes_allowed = False

    code: str = None
    description: str = None


class DutyExpressionParserV2(ValidityMixin, Writable, BaseTaricParser):
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


class DutyExpressionDescriptionParserV2(Writable, BaseTaricParser):
    model = DutyExpression
    parent_parser = DutyExpressionParserV2

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
    description: str = None


class MeasureTypeParserV2(ValidityMixin, Writable, BaseTaricParser):
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


class MeasureTypeDescriptionParserV2(Writable, BaseTaricParser):
    model = MeasureType
    parent_parser = MeasureTypeParserV2

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
    description: str = None


class AdditionalCodeTypeMeasureTypeParserV2(
    ValidityMixin,
    Writable,
    BaseTaricParser,
):
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


class MeasureConditionCodeParserV2(ValidityMixin, Writable, BaseTaricParser):
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


class MeasureConditionCodeDescriptionParserV2(Writable, BaseTaricParser):
    model = MeasureConditionCode
    parent_parser = MeasureConditionCodeParserV2

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
    description: str = None


class MeasureActionParserV2(ValidityMixin, Writable, BaseTaricParser):
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


class MeasureActionDescriptionParserV2(Writable, BaseTaricParser):
    model = MeasureAction
    parent_parser = MeasureActionParserV2

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
    description: str = None


class MeasureParserV2(ValidityMixin, Writable, BaseTaricParser):
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


class MeasureComponentParserV2(Writable, BaseTaricParser):
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
        "duty_expression__sid",
    ]

    component_measure__sid: int = None
    duty_expression__sid: int = None
    duty_amount: float = None
    monetary_unit__code: str = None
    component_measurement__measurement_unit__code: str = None
    component_measurement__measurement_unit_qualifier__code: str = None


class MeasureConditionParserV2(Writable, BaseTaricParser):
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


class MeasureConditionComponentParserV2(Writable, BaseTaricParser):
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


class MeasureExcludedGeographicalAreaParserV2(Writable, BaseTaricParser):
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


class FootnoteAssociationMeasureParserV2(Writable, BaseTaricParser):
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
