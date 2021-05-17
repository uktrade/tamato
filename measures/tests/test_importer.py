import pytest

from common.tests import factories
from measures import serializers
from measures import unit_serializers
from measures.validators import OrderNumberCaptureCode
from quotas.validators import AdministrationMechanism

pytestmark = pytest.mark.django_db


def test_measure_type_series_importer(imported_fields_match):
    assert imported_fields_match(
        factories.MeasureTypeSeriesFactory,
        serializers.MeasureTypeSeriesSerializer,
    )


def test_measurement_unit_importer(imported_fields_match):
    assert imported_fields_match(
        factories.MeasurementUnitFactory,
        serializer=unit_serializers.MeasurementUnitSerializer,
    )


def test_measurement_unit_qualifier_importer(imported_fields_match):
    assert imported_fields_match(
        factories.MeasurementUnitQualifierFactory,
        serializer=unit_serializers.MeasurementUnitQualifierSerializer,
    )


def test_measurement_importer(imported_fields_match):
    assert imported_fields_match(
        factories.MeasurementFactory,
        serializers.MeasurementSerializer,
        dependencies={
            "measurement_unit": factories.MeasurementUnitFactory,
            "measurement_unit_qualifier": factories.MeasurementUnitQualifierFactory,
        },
    )


def test_monetary_unit_importer(imported_fields_match):
    assert imported_fields_match(
        factories.MonetaryUnitFactory,
        serializer=unit_serializers.MonetaryUnitSerializer,
    )


def test_duty_expression_importer(imported_fields_match):
    assert imported_fields_match(
        factories.DutyExpressionFactory,
        serializers.DutyExpressionSerializer,
    )


def test_measure_type_importer(imported_fields_match):
    assert imported_fields_match(
        factories.MeasureTypeFactory,
        serializers.MeasureTypeSerializer,
        dependencies={
            "measure_type_series": factories.MeasureTypeSeriesFactory,
        },
    )


def test_additional_code_type_measure_type_importer(imported_fields_match):
    assert imported_fields_match(
        factories.AdditionalCodeTypeMeasureTypeFactory,
        serializers.AdditionalCodeTypeMeasureTypeSerializer,
        dependencies={
            "measure_type": factories.MeasureTypeFactory,
            "additional_code_type": factories.AdditionalCodeTypeFactory,
        },
    )


def test_measure_condition_code_importer(imported_fields_match):
    assert imported_fields_match(
        factories.MeasureConditionCodeFactory,
        serializers.MeasureConditionCodeSerializer,
    )


def test_measure_action_importer(imported_fields_match):
    assert imported_fields_match(
        factories.MeasureActionFactory,
        serializers.MeasureActionSerializer,
    )


def test_measure_importer(
    imported_fields_match,
    approved_transaction,
):
    rel = factories.AdditionalCodeTypeMeasureTypeFactory.create(
        measure_type__order_number_capture_code=OrderNumberCaptureCode.MANDATORY,
    )
    origin = factories.QuotaOrderNumberOriginFactory.create(
        order_number__mechanism=AdministrationMechanism.FCFS,
        transaction=approved_transaction,
    )
    ac = factories.AdditionalCodeFactory.create(type=rel.additional_code_type)

    assert imported_fields_match(
        factories.MeasureFactory,
        serializers.MeasureSerializer,
        dependencies={
            "measure_type": rel.measure_type,
            "geographical_area": origin.geographical_area,
            "goods_nomenclature": factories.GoodsNomenclatureFactory,
            "additional_code": ac,
            "order_number": origin.order_number,
            "generating_regulation": factories.RegulationFactory,
        },
    )


def test_measure_component_importer(imported_fields_match):
    assert imported_fields_match(
        factories.MeasureComponentFactory,
        serializers.MeasureComponentSerializer,
        dependencies={
            "component_measure": factories.MeasureFactory,
            "duty_expression": factories.DutyExpressionFactory,
            "monetary_unit": factories.MonetaryUnitFactory,
            "component_measurement": factories.MeasurementFactory,
        },
    )


def test_measure_condition_importer(imported_fields_match):
    assert imported_fields_match(
        factories.MeasureConditionFactory,
        serializers.MeasureConditionSerializer,
        dependencies={
            "dependent_measure": factories.MeasureFactory,
            "condition_code": factories.MeasureConditionCodeFactory,
            "monetary_unit": factories.MonetaryUnitFactory,
            "condition_measurement": factories.MeasurementFactory,
            "action": factories.MeasureActionFactory,
            "required_certificate": factories.CertificateFactory,
        },
    )


def test_measure_condition_component_importer(imported_fields_match):
    assert imported_fields_match(
        factories.MeasureConditionComponentFactory,
        serializers.MeasureConditionComponentSerializer,
        dependencies={
            "condition": factories.MeasureConditionFactory,
            "duty_expression": factories.DutyExpressionFactory,
            "monetary_unit": factories.MonetaryUnitFactory,
            "component_measurement": factories.MeasurementFactory,
        },
    )


def test_measure_excluded_geographical_area_importer(imported_fields_match):
    membership = factories.GeographicalMembershipFactory.create()

    assert imported_fields_match(
        factories.MeasureExcludedGeographicalAreaFactory,
        serializers.MeasureExcludedGeographicalAreaSerializer,
        dependencies={
            "modified_measure": factories.MeasureFactory.create(
                geographical_area=membership.geo_group,
            ),
            "excluded_geographical_area": membership.member,
        },
    )


def test_footnote_association_measure_importer(imported_fields_match):
    assert imported_fields_match(
        factories.FootnoteAssociationMeasureFactory,
        serializers.FootnoteAssociationMeasureSerializer,
        dependencies={
            "footnoted_measure": factories.MeasureFactory,
            "associated_footnote": factories.FootnoteFactory,
        },
    )
