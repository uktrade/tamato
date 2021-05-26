from datetime import date
from decimal import Decimal

from django.core.exceptions import ObjectDoesNotExist

from additional_codes.models import AdditionalCode
from additional_codes.models import AdditionalCodeType
from certificates.models import Certificate
from commodities.models import GoodsNomenclature
from common.validators import UpdateType
from footnotes.models import Footnote
from geo_areas.models import GeographicalArea
from importer.handlers import BaseHandler
from importer.taric import RecordParser
from measures import import_parsers as parsers
from measures import models
from measures import serializers
from measures import unit_serializers
from quotas.models import QuotaOrderNumber
from regulations.models import Regulation


class RegulationDoesNotExist(Exception):
    pass


class HandlerWithDutyAmount(BaseHandler):
    abstract = True

    def clean(self, data: dict) -> dict:
        if data.get("duty_amount"):
            data["duty_amount"] = Decimal(data["duty_amount"]).quantize(
                Decimal("1.000"),
            )

        return super().clean(data)


def get_measurement_link(model, kwargs):
    measurement_unit_code = kwargs.pop("measurement_unit__code", None)
    measurement_unit_qualifier_code = kwargs.pop(
        "measurement_unit_qualifier__code",
        None,
    )

    kwargs["measurement_unit"] = (
        models.MeasurementUnit.objects.get_latest_version(code=measurement_unit_code)
        if measurement_unit_code
        else None
    )
    kwargs["measurement_unit_qualifier"] = (
        models.MeasurementUnitQualifier.objects.get_latest_version(
            code=measurement_unit_qualifier_code,
        )
        if measurement_unit_qualifier_code
        else None
    )

    if not any(kwargs.values()):
        raise model.DoesNotExist

    return model.objects.latest_approved().get(**kwargs)


class MeasureTypeSeriesHandler(BaseHandler):
    serializer_class = serializers.MeasureTypeSeriesSerializer
    xml_model = parsers.MeasureTypeSeriesParser


@MeasureTypeSeriesHandler.register_dependant
class MeasureTypeSeriesDescriptionHandler(BaseHandler):
    dependencies = [MeasureTypeSeriesHandler]
    serializer_class = serializers.MeasureTypeSeriesSerializer
    xml_model = parsers.MeasureTypeSeriesDescriptionParser


class BaseMeasurementUnitHandler(BaseHandler):
    abstract = True
    serializer_class = unit_serializers.MeasurementUnitSerializer

    def post_save(self, obj: models.MeasurementUnit):
        if obj.update_type == UpdateType.CREATE:
            models.Measurement.objects.create(
                measurement_unit=obj,
                measurement_unit_qualifier=None,
                update_type=UpdateType.CREATE,
                valid_between=obj.valid_between,
                transaction=obj.transaction,
            )

        return super().post_save(obj)


@RecordParser.use_for_xml_serialization
class MeasurementUnitHandler(BaseMeasurementUnitHandler):
    xml_model = parsers.MeasurementUnitParser


@MeasurementUnitHandler.register_dependant  # TODO is this used in the db???
class MeasurementUnitDescriptionHandler(BaseMeasurementUnitHandler):
    dependencies = [MeasurementUnitHandler]
    xml_model = parsers.MeasurementUnitDescriptionParser


class MeasurementUnitQualifierHandler(BaseHandler):
    serializer_class = unit_serializers.MeasurementUnitQualifierSerializer
    xml_model = parsers.MeasurementUnitQualifierParser


@MeasurementUnitQualifierHandler.register_dependant
class MeasurementUnitQualifierDescriptionHandler(BaseHandler):
    dependencies = [MeasurementUnitQualifierHandler]
    serializer_class = unit_serializers.MeasurementUnitQualifierSerializer
    xml_model = parsers.MeasurementUnitQualifierDescriptionParser


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
    xml_model = parsers.MeasurementParser


class MonetaryUnitHandler(BaseHandler):
    serializer_class = unit_serializers.MonetaryUnitSerializer
    xml_model = parsers.MonetaryUnitParser


@MonetaryUnitHandler.register_dependant
class MonetaryUnitDescriptionHandler(BaseHandler):
    dependencies = [MonetaryUnitHandler]
    serializer_class = unit_serializers.MonetaryUnitSerializer
    xml_model = parsers.MonetaryUnitDescriptionParser


class DutyExpressionHandler(BaseHandler):
    serializer_class = serializers.DutyExpressionSerializer
    xml_model = parsers.DutyExpressionParser


@DutyExpressionHandler.register_dependant
class DutyExpressionDescriptionHandler(BaseHandler):
    dependencies = [DutyExpressionHandler]
    serializer_class = serializers.DutyExpressionSerializer
    xml_model = parsers.DutyExpressionDescriptionParser


class BaseMeasureTypeHandler(BaseHandler):
    links = (
        {
            "model": models.MeasureTypeSeries,
            "name": "measure_type_series",
        },
    )
    serializer_class = serializers.MeasureTypeSerializer
    abstract = True


class MeasureTypeHandler(BaseMeasureTypeHandler):
    serializer_class = serializers.MeasureTypeSerializer
    xml_model = parsers.MeasureTypeParser


@MeasureTypeHandler.register_dependant
class MeasureTypeDescriptionHandler(BaseMeasureTypeHandler):
    dependencies = [MeasureTypeHandler]
    serializer_class = serializers.MeasureTypeSerializer
    xml_model = parsers.MeasureTypeDescriptionParser


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
    xml_model = parsers.AdditionalCodeTypeMeasureTypeParser


class MeasureConditionCodeHandler(BaseHandler):
    serializer_class = serializers.MeasureConditionCodeSerializer
    xml_model = parsers.MeasureConditionCodeParser


@MeasureConditionCodeHandler.register_dependant
class MeasureConditionCodeDescriptionHandler(BaseHandler):
    dependencies = [MeasureConditionCodeHandler]
    serializer_class = serializers.MeasureConditionCodeSerializer
    xml_model = parsers.MeasureConditionCodeDescriptionParser


class MeasureActionHandler(BaseHandler):
    serializer_class = serializers.MeasureActionSerializer
    xml_model = parsers.MeasureActionParser


@MeasureActionHandler.register_dependant
class MeasureActionDescriptionHandler(BaseHandler):
    dependencies = [MeasureActionHandler]
    serializer_class = serializers.MeasureActionSerializer
    xml_model = parsers.MeasureActionDescriptionParser


class MeasureHandler(BaseHandler):
    identifying_fields = (
        "sid",
        "measure_type__sid",
        "geographical_area__sid",
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
            "identifying_fields": ("sid", "code", "type__sid"),
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
    xml_model = parsers.MeasureParser

    def load_link(self, name, model, identifying_fields=None, optional=False):
        if name == "terminating_regulation" and self.data.get(
            "terminating_regulation__regulation_id",
        ):
            optional = False
        return super().load_link(name, model, identifying_fields, optional)

    def get_order_number_link(self, model, kwargs):
        # XXX This seems like it might get the wrong object sometimes. Maybe we should
        # just store the order number string on the measure, rather than link it to a
        # QuotaOrderNumber instance?
        order_number = kwargs.pop("order_number")
        try:
            return model.objects.latest_approved().get(
                order_number=order_number,
                valid_between__contains=date.fromisoformat(
                    self.data["valid_between"]["lower"],
                ),
            )
        except ObjectDoesNotExist:
            if order_number:
                self.data["dead_order_number"] = order_number

    def get_additional_code_link(self, model, kwargs):
        try:
            return self.get_generic_link(model, kwargs)
        except model.DoesNotExist:
            if any(kwargs.values()):
                self.data["dead_additional_code"] = "|".join(
                    [
                        kwargs.get("sid") or "",
                        kwargs.get("code") or "",
                        kwargs.get("type__sid") or "",
                    ],
                )
            raise


class MeasureComponentHandler(HandlerWithDutyAmount):
    identifying_fields = (
        "component_measure__sid",
        "duty_expression__sid",
    )
    links = (
        {
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
    xml_model = parsers.MeasureComponentParser

    def get_component_measurement_link(self, model, kwargs):
        return get_measurement_link(model, kwargs)


class MeasureConditionHandler(HandlerWithDutyAmount):
    links = (
        {
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
            "identifying_fields": (
                "sid",
                "certificate_type__sid",
            ),
            "model": Certificate,
            "name": "required_certificate",
            "optional": True,
        },
    )
    serializer_class = serializers.MeasureConditionSerializer
    xml_model = parsers.MeasureConditionParser

    def get_condition_measurement_link(self, model, kwargs):
        if not any(kwargs.values()):
            raise model.DoesNotExist
        return get_measurement_link(model, kwargs)


class MeasureConditionComponentHandler(HandlerWithDutyAmount):
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
            "name": "component_measurement",
            "optional": True,
        },
    )
    serializer_class = serializers.MeasureConditionComponentSerializer
    xml_model = parsers.MeasureConditionComponentParser

    def get_component_measurement_link(self, model, kwargs):
        return get_measurement_link(model, kwargs)


class MeasureExcludedGeographicalAreaHandler(BaseHandler):
    identifying_fields = (
        "modified_measure__sid",
        "excluded_geographical_area__sid",
    )
    links = (
        {
            "model": models.Measure,
            "name": "modified_measure",
        },
        {
            "model": GeographicalArea,
            "name": "excluded_geographical_area",
        },
    )
    serializer_class = serializers.MeasureExcludedGeographicalAreaSerializer
    xml_model = parsers.MeasureExcludedGeographicalAreaParser


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
    xml_model = parsers.FootnoteAssociationMeasureParser
