from importer.namespaces import Tag
from importer.parsers import BooleanElement
from importer.parsers import ConstantElement
from importer.parsers import ElementParser
from importer.parsers import IntElement
from importer.parsers import TextElement
from importer.parsers import ValidityMixin
from importer.parsers import Writable
from importer.taric import RecordParser


@RecordParser.register_child("measure_type_series")
class MeasureTypeSeriesParser(ValidityMixin, Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="measure.type.series" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="measure.type.series.id" type="MeasureTypeSeriesId"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                    <xs:element name="measure.type.combination" type="MeasureTypeCombination"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    record_code = "140"
    subrecord_code = "00"

    tag = Tag("measure.type.series")

    sid = TextElement(Tag("measure.type.series.id"))
    valid_between_lower = ValidityMixin.valid_between_lower
    valid_between_upper = ValidityMixin.valid_between_upper
    measure_type_combination = IntElement(Tag("measure.type.combination"))


@RecordParser.register_child("measure.type.series.description")
class MeasureTypeSeriesDescriptionParser(Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="measure.type.series.description" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="measure.type.series.id" type="MeasureTypeSeriesId"/>
                    <xs:element name="language.id" type="LanguageId"/>
                    <xs:element name="description" type="ShortDescription" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    record_code = "140"
    subrecord_code = "05"

    tag = Tag("measure.type.series.description")

    sid = TextElement(Tag("measure.type.series.id"))
    language_id = ConstantElement(Tag("language.id"), value="EN")
    description = TextElement(Tag("description"))


@RecordParser.register_child("measurement_unit")
class MeasurementUnitParser(ValidityMixin, Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="measurement.unit" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="measurement.unit.code" type="MeasurementUnitCode"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    record_code = "210"
    subrecord_code = "00"

    tag = Tag("measurement.unit")

    code = TextElement(Tag("measurement.unit.code"))
    valid_between_lower = ValidityMixin.valid_between_lower
    valid_between_upper = ValidityMixin.valid_between_upper


@RecordParser.register_child("measurement_unit_description")
class MeasurementUnitDescriptionParser(Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="measurement.unit.description" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="measurement.unit.code" type="MeasurementUnitCode"/>
                    <xs:element name="language.id" type="LanguageId"/>
                    <xs:element name="description" type="ShortDescription" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    record_code = "210"
    subrecord_code = "05"

    tag = Tag("measurement.unit.description")

    code = TextElement(Tag("measurement.unit.code"))
    language_id = ConstantElement(Tag("language.id"), value="EN")
    description = TextElement(Tag("description"))


@RecordParser.register_child("measurement_unit_qualifier")
class MeasurementUnitQualifierParser(ValidityMixin, Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="measurement.unit.qualifier" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="measurement.unit.qualifier.code" type="MeasurementUnitQualifierCode"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    record_code = "215"
    subrecord_code = "00"

    tag = Tag("measurement.unit.qualifier")

    code = TextElement(Tag("measurement.unit.qualifier.code"))
    valid_between_lower = ValidityMixin.valid_between_lower
    valid_between_upper = ValidityMixin.valid_between_upper


@RecordParser.register_child("measurement_unit_qualifier_description")
class MeasurementUnitQualifierDescriptionParser(Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="measurement.unit.qualifier.description" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="measurement.unit.qualifier.code" type="MeasurementUnitQualifierCode"/>
                    <xs:element name="language.id" type="LanguageId"/>
                    <xs:element name="description" type="ShortDescription" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    record_code = "215"
    subrecord_code = "05"

    tag = Tag("measurement.unit.qualifier.description")

    code = TextElement(Tag("measurement.unit.qualifier.code"))
    language_id = ConstantElement(Tag("language.id"), value="EN")
    description = TextElement(Tag("description"))


@RecordParser.register_child("measurement")
class MeasurementParser(ValidityMixin, Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="measurement" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="measurement.unit.code" type="MeasurementUnitCode"/>
                    <xs:element name="measurement.unit.qualifier.code" type="MeasurementUnitQualifierCode"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    record_code = "220"
    subrecord_code = "00"

    tag = Tag("measurement")

    measurement_unit__code = TextElement(Tag("measurement.unit.code"))
    measurement_unit_qualifier__code = TextElement(
        Tag("measurement.unit.qualifier.code"),
    )
    valid_between_lower = ValidityMixin.valid_between_lower
    valid_between_upper = ValidityMixin.valid_between_upper


@RecordParser.register_child("monetary_unit")
class MonetaryUnitParser(ValidityMixin, Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="monetary.unit" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="monetary.unit.code" type="MonetaryUnitCode"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    record_code = "225"
    subrecord_code = "00"

    tag = Tag("monetary.unit")

    code = TextElement(Tag("monetary.unit.code"))
    valid_between_lower = ValidityMixin.valid_between_lower
    valid_between_upper = ValidityMixin.valid_between_upper


@RecordParser.register_child("monetary_unit_description")
class MonetaryUnitDescriptionParser(Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="monetary.unit.description" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="monetary.unit.code" type="MonetaryUnitCode"/>
                    <xs:element name="language.id" type="LanguageId"/>
                    <xs:element name="description" type="ShortDescription" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    record_code = "225"
    subrecord_code = "05"

    tag = Tag("monetary.unit.description")

    code = TextElement(Tag("monetary.unit.code"))
    language_id = ConstantElement(Tag("language.id"), value="EN")
    description = TextElement(Tag("description"))


@RecordParser.register_child("duty_expression")
class DutyExpressionParser(ValidityMixin, Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="duty.expression" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="duty.expression.id" type="DutyExpressionId"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                    <xs:element name="duty.amount.applicability.code" type="DutyAmountApplicabilityCode"/>
                    <xs:element name="measurement.unit.applicability.code" type="MeasurementUnitApplicabilityCode"/>
                    <xs:element name="monetary.unit.applicability.code" type="MonetaryUnitApplicabilityCode"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    record_code = "230"
    subrecord_code = "00"

    tag = Tag("duty.expression")

    sid = IntElement(Tag("duty.expression.id"), format="FM00")
    valid_between_lower = ValidityMixin.valid_between_lower
    valid_between_upper = ValidityMixin.valid_between_upper
    duty_amount_applicability_code = IntElement(
        Tag("duty.amount.applicability.code"),
    )
    measurement_unit_applicability_code = IntElement(
        Tag("measurement.unit.applicability.code"),
    )
    monetary_unit_applicability_code = IntElement(
        Tag("monetary.unit.applicability.code"),
    )


@RecordParser.register_child("duty_expression_description")
class DutyExpressionDescriptionParser(Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="duty.expression.description" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="duty.expression.id" type="DutyExpressionId"/>
                    <xs:element name="language.id" type="LanguageId"/>
                    <xs:element name="description" type="ShortDescription" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    record_code = "230"
    subrecord_code = "05"

    tag = Tag("duty.expression.description")

    sid = DutyExpressionParser.sid
    language_id = ConstantElement(Tag("language.id"), value="EN")
    description = TextElement(Tag("description"))


@RecordParser.register_child("measure_type")
class MeasureTypeParser(ValidityMixin, Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="measure.type" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="measure.type.id" type="MeasureTypeId"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                    <xs:element name="trade.movement.code" type="TradeMovementCode"/>
                    <xs:element name="priority.code" type="PriorityCode"/>
                    <xs:element name="measure.component.applicable.code" type="MeasurementUnitApplicabilityCode"/>
                    <xs:element name="origin.dest.code" type="OriginCode"/>
                    <xs:element name="order.number.capture.code" type="OrderNumberCaptureCode"/>
                    <xs:element name="measure.explosion.level" type="MeasureExplosionLevel"/>
                    <xs:element name="measure.type.series.id" type="MeasureTypeSeriesId"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    record_code = "235"
    subrecord_code = "00"

    tag = Tag("measure.type")

    sid = TextElement(Tag("measure.type.id"))
    valid_between_lower = ValidityMixin.valid_between_lower
    valid_between_upper = ValidityMixin.valid_between_upper
    trade_movement_code = IntElement(Tag("trade.movement.code"))
    priority_code = IntElement(Tag("priority.code"))
    measure_component_applicability_code = IntElement(
        Tag("measure.component.applicable.code"),
    )
    origin_destination_code = IntElement(Tag("origin.dest.code"))
    order_number_capture_code = IntElement(Tag("order.number.capture.code"))
    measure_explosion_level = IntElement(Tag("measure.explosion.level"))
    measure_type_series__sid = TextElement(Tag("measure.type.series.id"))


@RecordParser.register_child("measure_type_description")
class MeasureTypeDescriptionParser(Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="measure.type.description" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="measure.type.id" type="MeasureTypeId"/>
                    <xs:element name="language.id" type="LanguageId"/>
                    <xs:element name="description" type="ShortDescription" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    record_code = "235"
    subrecord_code = "05"

    tag = Tag("measure.type.description")

    sid = TextElement(Tag("measure.type.id"))
    language_id = ConstantElement(Tag("language.id"), value="EN")
    description = TextElement(Tag("description"))


@RecordParser.register_child("additional_code_type_measure_type")
class AdditionalCodeTypeMeasureTypeParser(ValidityMixin, Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="additional.code.type.measure.type" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="measure.type.id" type="MeasureTypeId"/>
                    <xs:element name="additional.code.type.id" type="AdditionalCodeTypeId"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    record_code = "240"
    subrecord_code = "00"

    tag = Tag("additional.code.type.measure.type")

    measure_type__sid = TextElement(Tag("measure.type.id"))
    additional_code_type__sid = TextElement(Tag("additional.code.type.id"))
    valid_between_lower = ValidityMixin.valid_between_lower
    valid_between_upper = ValidityMixin.valid_between_upper


@RecordParser.register_child("measure_condition_code")
class MeasureConditionCodeParser(ValidityMixin, Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="measure.condition.code" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="condition.code" type="ConditionCode"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    record_code = "350"
    subrecord_code = "00"

    tag = Tag("measure.condition.code")

    code = TextElement(Tag("condition.code"))
    valid_between_lower = ValidityMixin.valid_between_lower
    valid_between_upper = ValidityMixin.valid_between_upper


@RecordParser.register_child("measure_condition_code_description")
class MeasureConditionCodeDescriptionParser(Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="measure.condition.code.description" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="condition.code" type="ConditionCode"/>
                    <xs:element name="language.id" type="LanguageId"/>
                    <xs:element name="description" type="ShortDescription" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    record_code = "350"
    subrecord_code = "05"

    tag = Tag("measure.condition.code.description")

    code = TextElement(Tag("condition.code"))
    language_id = ConstantElement(Tag("language.id"), value="EN")
    description = TextElement(Tag("description"))


@RecordParser.register_child("measure_action")
class MeasureActionParser(ValidityMixin, Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="measure.action" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="action.code" type="ActionCode"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    record_code = "355"
    subrecord_code = "00"

    tag = Tag("measure.action")

    code = TextElement(Tag("action.code"))
    valid_between_lower = ValidityMixin.valid_between_lower
    valid_between_upper = ValidityMixin.valid_between_upper


@RecordParser.register_child("measure_action_description")
class MeasureActionDescriptionParser(Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="measure.action.description" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="action.code" type="ActionCode"/>
                    <xs:element name="language.id" type="LanguageId"/>
                    <xs:element name="description" type="ShortDescription" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    record_code = "355"
    subrecord_code = "05"

    tag = Tag("measure.action.description")

    code = TextElement(Tag("action.code"))
    language_id = ConstantElement(Tag("language.id"), value="EN")
    description = TextElement(Tag("description"))


@RecordParser.register_child("measure")
class MeasureParser(ValidityMixin, Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="measure" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="measure.sid" type="SID"/>
                    <xs:element name="measure.type" type="MeasureTypeId"/>
                    <xs:element name="geographical.area" type="GeographicalAreaId"/>
                    <xs:element name="goods.nomenclature.item.id" type="GoodsNomenclatureItemId" minOccurs="0"/>
                    <xs:element name="additional.code.type" type="AdditionalCodeTypeId" minOccurs="0"/>
                    <xs:element name="additional.code" type="AdditionalCode" minOccurs="0"/>
                    <xs:element name="ordernumber" type="OrderNumber" minOccurs="0"/>
                    <xs:element name="reduction.indicator" type="ReductionIndicator" minOccurs="0"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="measure.generating.regulation.role" type="RegulationRoleTypeId"/>
                    <xs:element name="measure.generating.regulation.id" type="RegulationId"/>
                    <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                    <xs:element name="justification.regulation.role" type="RegulationRoleTypeId" minOccurs="0"/>
                    <xs:element name="justification.regulation.id" type="RegulationId" minOccurs="0"/>
                    <xs:element name="stopped.flag" type="StoppedFlag"/>
                    <xs:element name="geographical.area.sid" type="SID" minOccurs="0"/>
                    <xs:element name="goods.nomenclature.sid" type="SID" minOccurs="0"/>
                    <xs:element name="additional.code.sid" type="SID" minOccurs="0"/>
                    <xs:element name="export.refund.nomenclature.sid" type="SID" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    record_code = "430"
    subrecord_code = "00"

    tag = Tag("measure")

    sid = TextElement(Tag("measure.sid"))
    measure_type__sid = TextElement(Tag("measure.type"))
    geographical_area__area_id = TextElement(Tag("geographical.area"))
    goods_nomenclature__item_id = TextElement(Tag("goods.nomenclature.item.id"))
    additional_code__type__sid = TextElement(Tag("additional.code.type"))
    additional_code__code = TextElement(Tag("additional.code"))
    order_number__order_number = TextElement(Tag("ordernumber"))
    reduction = IntElement(Tag("reduction.indicator"))
    valid_between_lower = ValidityMixin.valid_between_lower
    generating_regulation__role_type = IntElement(
        Tag("measure.generating.regulation.role"),
    )
    generating_regulation__regulation_id = TextElement(
        Tag("measure.generating.regulation.id"),
    )
    valid_between_upper = ValidityMixin.valid_between_upper
    terminating_regulation__role_type = IntElement(
        Tag("justification.regulation.role"),
    )
    terminating_regulation__regulation_id = TextElement(
        Tag("justification.regulation.id"),
    )
    stopped = BooleanElement(Tag("stopped.flag"))
    geographical_area__sid = TextElement(Tag("geographical.area.sid"))
    goods_nomenclature__sid = TextElement(Tag("goods.nomenclature.sid"))
    additional_code__sid = TextElement(Tag("additional.code.sid"))


@RecordParser.register_child("measure_component")
class MeasureComponentParser(Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="measure.component" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="measure.sid" type="SID"/>
                    <xs:element name="duty.expression.id" type="DutyExpressionId"/>
                    <xs:element name="duty.amount" type="DutyAmount" minOccurs="0"/>
                    <xs:element name="monetary.unit.code" type="MonetaryUnitCode" minOccurs="0"/>
                    <xs:element name="measurement.unit.code" type="MeasurementUnitCode" minOccurs="0"/>
                    <xs:element name="measurement.unit.qualifier.code" type="MeasurementUnitQualifierCode" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    record_code = "430"
    subrecord_code = "05"

    tag = Tag("measure.component")

    component_measure__sid = TextElement(Tag("measure.sid"))
    duty_expression__sid = DutyExpressionParser.sid
    duty_amount = TextElement(Tag("duty.amount"))
    monetary_unit__code = TextElement(Tag("monetary.unit.code"))
    component_measurement__measurement_unit__code = TextElement(
        Tag("measurement.unit.code"),
    )
    component_measurement__measurement_unit_qualifier__code = TextElement(
        Tag("measurement.unit.qualifier.code"),
    )


@RecordParser.register_child("measure_condition")
class MeasureConditionParser(Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="measure.condition" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="measure.condition.sid" type="SID"/>
                    <xs:element name="measure.sid" type="SID"/>
                    <xs:element name="condition.code" type="ConditionCode"/>
                    <xs:element name="component.sequence.number" type="ComponentSequenceNumber"/>
                    <xs:element name="condition.duty.amount" type="DutyAmount" minOccurs="0"/>
                    <xs:element name="condition.monetary.unit.code" type="MonetaryUnitCode" minOccurs="0"/>
                    <xs:element name="condition.measurement.unit.code" type="MeasurementUnitCode" minOccurs="0"/>
                    <xs:element name="condition.measurement.unit.qualifier.code" type="MeasurementUnitQualifierCode" minOccurs="0"/>
                    <xs:element name="action.code" type="ActionCode" minOccurs="0"/>
                    <xs:element name="certificate.type.code" type="CertificateTypeCode" minOccurs="0"/>
                    <xs:element name="certificate.code" type="CertificateCode" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    record_code = "430"
    subrecord_code = "10"

    tag = Tag("measure.condition")

    sid = TextElement(Tag("measure.condition.sid"))
    dependent_measure__sid = TextElement(Tag("measure.sid"))
    condition_code__code = TextElement(Tag("condition.code"))
    component_sequence_number = IntElement(Tag("component.sequence.number"))
    duty_amount = TextElement(Tag("condition.duty.amount"))
    monetary_unit__code = TextElement(Tag("condition.monetary.unit.code"))
    condition_measurement__measurement_unit__code = TextElement(
        Tag("condition.measurement.unit.code"),
    )
    condition_measurement__measurement_unit_qualifier__code = TextElement(
        Tag("condition.measurement.unit.qualifier.code"),
    )
    action__code = TextElement(Tag("action.code"))
    required_certificate__certificate_type__sid = TextElement(
        Tag("certificate.type.code"),
    )
    required_certificate__sid = TextElement(Tag("certificate.code"))


@RecordParser.register_child("measure_condition_component")
class MeasureConditionComponentParser(Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="measure.condition.component" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="measure.condition.sid" type="SID"/>
                    <xs:element name="duty.expression.id" type="DutyExpressionId"/>
                    <xs:element name="duty.amount" type="DutyAmount" minOccurs="0"/>
                    <xs:element name="monetary.unit.code" type="MonetaryUnitCode" minOccurs="0"/>
                    <xs:element name="measurement.unit.code" type="MeasurementUnitCode" minOccurs="0"/>
                    <xs:element name="measurement.unit.qualifier.code" type="MeasurementUnitQualifierCode" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    record_code = "430"
    subrecord_code = "11"

    tag = Tag("measure.condition.component")

    condition__sid = TextElement(Tag("measure.condition.sid"))
    duty_expression__sid = DutyExpressionParser.sid
    duty_amount = TextElement(Tag("duty.amount"))
    monetary_unit__code = TextElement(Tag("monetary.unit.code"))
    component_measurement__measurement_unit__code = TextElement(
        Tag("measurement.unit.code"),
    )
    component_measurement__measurement_unit_qualifier__code = TextElement(
        Tag("measurement.unit.qualifier.code"),
    )


@RecordParser.register_child("measure_excluded_geographical_area")
class MeasureExcludedGeographicalAreaParser(Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="measure.excluded.geographical.area" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="measure.sid" type="SID"/>
                    <xs:element name="excluded.geographical.area" type="GeographicalAreaId"/>
                    <xs:element name="geographical.area.sid" type="SID"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    record_code = "430"
    subrecord_code = "15"

    tag = Tag("measure.excluded.geographical.area")

    modified_measure__sid = TextElement(Tag("measure.sid"))
    excluded_geographical_area__area_id = TextElement(
        Tag("excluded.geographical.area"),
    )
    excluded_geographical_area__sid = TextElement(Tag("geographical.area.sid"))


@RecordParser.register_child("footnote_association_measure")
class FootnoteAssociationMeasureParser(Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="footnote.association.measure" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="measure.sid" type="SID"/>
                    <xs:element name="footnote.type.id" type="FootnoteTypeId"/>
                    <xs:element name="footnote.id" type="FootnoteId"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    record_code = "430"
    subrecord_code = "20"

    tag = Tag("footnote.association.measure")

    footnoted_measure__sid = TextElement(Tag("measure.sid"))
    associated_footnote__footnote_type__footnote_type_id = TextElement(
        Tag("footnote.type.id"),
    )
    associated_footnote__footnote_id = TextElement(Tag("footnote.id"))
