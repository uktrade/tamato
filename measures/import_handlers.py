from additional_codes.models import AdditionalCode
from additional_codes.models import AdditionalCodeType
from certificates.models import Certificate
from commodities.models import GoodsNomenclature
from footnotes.models import Footnote
from footnotes.models import FootnoteType
from geo_areas.models import GeographicalArea
from importer.handlers import BaseHandler
from measures import import_parsers as parsers
from measures import models
from measures import serializers
from measures import unit_serializers
from quotas.models import QuotaOrderNumber
from regulations.models import Regulation


class MeasureTypeSeriesHandler(BaseHandler):
    serializer_class = serializers.MeasureTypeSeriesSerializer
    tag = parsers.MeasureTypeSeriesParser.tag.name


@MeasureTypeSeriesHandler.register_dependant
class MeasureTypeSeriesDescriptionHandler(BaseHandler):
    dependencies = [MeasureTypeSeriesHandler]
    serializer_class = serializers.MeasureTypeSeriesSerializer
    tag = parsers.MeasureTypeSeriesDescriptionParser.tag.name


class MeasurementUnitHandler(BaseHandler):
    serializer_class = unit_serializers.MeasurementUnitSerializer
    tag = parsers.MeasurementUnitParser.tag.name


@MeasurementUnitHandler.register_dependant
class MeasurementUnitDescriptionHandler(BaseHandler):
    dependencies = [MeasurementUnitHandler]
    serializer_class = unit_serializers.MeasurementUnitSerializer
    tag = parsers.MeasurementUnitDescriptionParser.tag.name


class MeasurementUnitQualifierHandler(BaseHandler):
    serializer_class = unit_serializers.MeasurementUnitQualifierSerializer
    tag = parsers.MeasurementUnitQualifierParser.tag.name


@MeasurementUnitQualifierHandler.register_dependant
class MeasurementUnitQualifierDescriptionHandler(BaseHandler):
    dependencies = [MeasurementUnitQualifierHandler]
    serializer_class = unit_serializers.MeasurementUnitQualifierSerializer
    tag = parsers.MeasurementUnitQualifierDescriptionParser.tag.name


class MeasurementHandler(BaseHandler):
    identifying_fields = ("measurement_unit__code", "measurement_unit_qualifier__code")
    links = (
        {
            "model": models.MeasurementUnit,
            "name": "measurement_unit",
        },
        {
            "model": models.MeasurementUnitQualifier,
            "name": "measurement_unit_qualifier",
        },
    )
    serializer_class = unit_serializers.MeasurementSerializer
    tag = parsers.MeasurementParser.tag.name


class MonetaryUnitHandler(BaseHandler):
    serializer_class = unit_serializers.MonetaryUnitSerializer
    tag = parsers.MonetaryUnitParser.tag.name


@MonetaryUnitHandler.register_dependant
class MonetaryUnitDescriptionHandler(BaseHandler):
    dependencies = [MonetaryUnitHandler]
    serializer_class = unit_serializers.MonetaryUnitSerializer
    tag = parsers.MonetaryUnitDescriptionParser.tag.name


class DutyExpressionHandler(BaseHandler):
    serializer_class = serializers.DutyExpressionSerializer
    tag = parsers.DutyExpressionParser.tag.name


@DutyExpressionHandler.register_dependant
class DutyExpressionDescriptionHandler(BaseHandler):
    dependencies = [DutyExpressionHandler]
    serializer_class = serializers.DutyExpressionSerializer
    tag = parsers.DutyExpressionDescriptionParser.tag.name


class BaseMeasureTypeHandler(BaseHandler):
    links = (
        {
            "model": models.MeasureTypeSeries,
            "name": "measure_type_series",
        },
    )
    serializer_class = serializers.MeasureTypeSerializer
    tag = "BaseMeasureTypeHandler"


class MeasureTypeHandler(BaseMeasureTypeHandler):
    serializer_class = serializers.MeasureTypeSerializer
    tag = parsers.MeasureTypeParser.tag.name


@MeasureTypeHandler.register_dependant
class MeasureTypeDescriptionHandler(BaseMeasureTypeHandler):
    dependencies = [MeasureTypeHandler]
    serializer_class = serializers.MeasureTypeSerializer
    tag = parsers.MeasureTypeDescriptionParser.tag.name


class AdditionalCodeTypeMeasureTypeHandler(BaseHandler):
    identifying_fields = ("measure_type__sid", "additional_code_type__sid")
    links = (
        {
            "model": models.MeasureType,
            "name": "measure_type",
        },
        {
            "model": AdditionalCodeType,
            "name": "additional_code_type",
        },
    )
    serializer_class = serializers.AdditionalCodeTypeMeasureTypeSerializer
    tag = parsers.AdditionalCodeTypeMeasureTypeParser.tag.name


class MeasureConditionCodeHandler(BaseHandler):
    serializer_class = serializers.MeasureConditionCodeSerializer
    tag = parsers.MeasureConditionCodeParser.tag.name


@MeasureConditionCodeHandler.register_dependant
class MeasureConditionCodeDescriptionHandler(BaseHandler):
    dependencies = [MeasureConditionCodeHandler]
    serializer_class = serializers.MeasureConditionCodeSerializer
    tag = parsers.MeasureConditionCodeDescriptionParser.tag.name


class MeasureActionHandler(BaseHandler):
    serializer_class = serializers.MeasureActionSerializer
    tag = parsers.MeasureActionParser.tag.name


@MeasureActionHandler.register_dependant
class MeasureActionDescriptionHandler(BaseHandler):
    dependencies = [MeasureActionHandler]
    serializer_class = serializers.MeasureActionSerializer
    tag = parsers.MeasureActionDescriptionParser.tag.name


class MeasureHandler(BaseHandler):
    identifying_fields = (
        "measure_type__sid",
        "geographical_area__sid",
        "goods_nomenclature__sid",
        "additional_code__sid",
        "order_number__order_number",
        "reduction",
    )
    links = (
        {
            "model": models.MeasureType,
            "name": "measure_type",
        },
        {
            "model": GeographicalArea,
            "name": "geographical_area",
        },
        {
            "model": GoodsNomenclature,
            "name": "goods_nomenclature",
            "optional": True,
        },
        {
            "model": AdditionalCode,
            "name": "additional_code",
            "optional": True,
        },
        {
            "identifying_fields": (
                "sid",
                "order_number",
            ),
            "model": QuotaOrderNumber,
            "name": "order_number",
            "optional": True,
        },
        {
            "model": Regulation,
            "name": "generating_regulation",
        },
        {
            "model": Regulation,
            "name": "terminating_regulation",
            "optional": True,
        },
    )
    serializer_class = serializers.MeasureSerializer
    tag = parsers.MeasureParser.tag.name

    def get_order_number_link(self, model, kwargs):
        # XXX This seems like it might get the wrong object sometimes. Maybe we should
        # just store the order number string on the measure, rather than link it to a
        # QuotaOrderNumber instance?
        return model.objects.current().get(
            order_number=kwargs.pop("order_number"),
        )


class MeasureComponentHandler(BaseHandler):
    identifying_fields = (
        "component_measure__sid",
        "duty_expression__sid",
    )
    links = (
        {
            "identifying_fields": ("sid",),
            "model": models.Measure,
            "name": "component_measure",
        },
        {
            "model": models.DutyExpression,
            "name": "duty_expression",
        },
        {
            "model": models.MonetaryUnit,
            "name": "monetary_unit",
            "optional": True,
        },
        {
            "identifying_fields": (
                "measurement_unit__code",
                "measurement_unit_qualifier__code",
            ),
            "model": models.Measurement,
            "name": "component_measurement",
            "optional": True,
        },
    )
    serializer_class = serializers.MeasureComponentSerializer
    tag = parsers.MeasureComponentParser.tag.name

    def get_component_measure_link(self, model, kwargs):
        return model.objects.current().get(
            sid=kwargs.pop("sid"),
        )

    def get_component_measurement_link(self, model, kwargs):
        return model.objects.get_latest_version(
            measurement_unit=models.MeasurementUnit.objects.get_latest_version(
                code=kwargs.pop("measurement_unit__code")
            ),
            measurement_unit_qualifier=models.MeasurementUnitQualifier.objects.get_latest_version(
                code=kwargs.pop("measurement_unit_qualifier__code")
            ),
            **kwargs,
        )


class MeasureConditionHandler(BaseHandler):
    links = (
        {
            "identifying_fields": ("sid",),
            "model": models.Measure,
            "name": "dependent_measure",
        },
        {
            "model": models.MeasureConditionCode,
            "name": "condition_code",
        },
        {
            "model": models.MonetaryUnit,
            "name": "monetary_unit",
            "optional": True,
        },
        {
            "identifying_fields": (
                "measurement_unit__code",
                "measurement_unit_qualifier__code",
            ),
            "model": models.Measurement,
            "name": "condition_measurement",
            "optional": True,
        },
        {
            "model": models.MeasureAction,
            "name": "action",
            "optional": True,
        },
        {
            "model": Certificate,
            "name": "required_certificate",
            "optional": True,
        },
    )
    serializer_class = serializers.MeasureConditionSerializer
    tag = parsers.MeasureConditionParser.tag.name

    def get_dependent_measure_link(self, model, kwargs):
        return model.objects.current().get(
            sid=kwargs.pop("sid"),
        )

    def get_condition_measurement_link(self, model, kwargs):
        return model.objects.get_latest_version(
            measurement_unit=models.MeasurementUnit.objects.get_latest_version(
                code=kwargs.pop("measurement_unit__code")
            ),
            measurement_unit_qualifier=models.MeasurementUnitQualifier.objects.get_latest_version(
                code=kwargs.pop("measurement_unit_qualifier__code")
            ),
            **kwargs,
        )


class MeasureConditionComponentHandler(BaseHandler):
    identifying_fields = ("condition__sid", "duty_expression__sid")
    links = (
        {
            "model": models.MeasureCondition,
            "name": "condition",
        },
        {
            "model": models.DutyExpression,
            "name": "duty_expression",
        },
        {
            "model": models.MonetaryUnit,
            "name": "monetary_unit",
            "optional": True,
        },
        {
            "identifying_fields": (
                "measurement_unit__code",
                "measurement_unit_qualifier__code",
            ),
            "model": models.Measurement,
            "name": "condition_component_measurement",
            "optional": True,
        },
    )
    serializer_class = serializers.MeasureConditionComponentSerializer
    tag = parsers.MeasureConditionComponentParser.tag.name

    def get_condition_component_measurement_link(self, model, kwargs):
        return model.objects.get_latest_version(
            measurement_unit=models.MeasurementUnit.objects.get_latest_version(
                code=kwargs.pop("measurement_unit__code")
            ),
            measurement_unit_qualifier=models.MeasurementUnitQualifier.objects.get_latest_version(
                code=kwargs.pop("measurement_unit_qualifier__code")
            ),
            **kwargs,
        )


class MeasureExcludedGeographicalAreaHandler(BaseHandler):
    identifying_fields = (
        "modified_measure__sid",
        "excluded_geographical_area__sid",
    )
    links = (
        {
            "identifying_fields": ("sid",),
            "model": models.Measure,
            "name": "modified_measure",
        },
        {
            "model": GeographicalArea,
            "name": "excluded_geographical_area",
        },
    )
    serializer_class = serializers.MeasureExcludedGeographicalAreaSerializer
    tag = parsers.MeasureExcludedGeographicalAreaParser.tag.name

    def get_modified_measure_link(self, model, kwargs):
        return model.objects.current().get(
            sid=kwargs.pop("sid"),
        )


class FootnoteAssociationMeasureHandler(BaseHandler):
    identifying_fields = (
        "footnoted_measure__sid",
        "associated_footnote__footnote_type__footnote_type_id",
        "associated_footnote__footnote_id",
    )
    links = (
        {
            "identifying_fields": ("sid",),
            "model": models.Measure,
            "name": "footnoted_measure",
        },
        {
            "identifying_fields": (
                "footnote_type__footnote_type_id",
                "footnote_id",
            ),
            "model": Footnote,
            "name": "associated_footnote",
        },
    )
    serializer_class = serializers.FootnoteAssociationMeasureSerializer
    tag = parsers.FootnoteAssociationMeasureParser.tag.name

    def get_footnoted_measure_link(self, model, kwargs):
        return model.objects.current().get(
            sid=kwargs.pop("sid"),
        )

    def get_associated_footnote_link(self, model, kwargs):
        return model.objects.get_latest_version(
            footnote_type=FootnoteType.objects.get_latest_version(
                footnote_type_id=kwargs.pop("footnote_type__footnote_type_id"),
            ),
            footnote_id=kwargs.pop("footnote_id"),
            **kwargs,
        )
