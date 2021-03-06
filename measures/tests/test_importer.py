import pytest

from common.tests import factories
from common.validators import UpdateType
from measures import serializers
from measures import unit_serializers
from measures.validators import OrderNumberCaptureCode
from quotas.validators import AdministrationMechanism


pytestmark = pytest.mark.django_db


def test_measure_type_series_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.MeasureTypeSeriesFactory, serializers.MeasureTypeSeriesSerializer
    )


def test_measure_type_series_importer_update(update_imported_fields_match):
    assert update_imported_fields_match(
        factories.MeasureTypeSeriesFactory, serializers.MeasureTypeSeriesSerializer
    )


def test_measurement_unit_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.MeasurementUnitFactory,
        serializer=unit_serializers.MeasurementUnitSerializer,
    )


def test_measurement_unit_importer_update(update_imported_fields_match):
    assert update_imported_fields_match(
        factories.MeasurementUnitFactory, unit_serializers.MeasurementUnitSerializer
    )


def test_measurement_unit_qualifier_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.MeasurementUnitQualifierFactory,
        serializer=unit_serializers.MeasurementUnitQualifierSerializer,
    )


def test_measurement_unit_qualifier_importer_update(update_imported_fields_match):
    assert update_imported_fields_match(
        factories.MeasurementUnitQualifierFactory,
        unit_serializers.MeasurementUnitQualifierSerializer,
    )


def test_measurement_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.MeasurementFactory.build(
            measurement_unit=factories.MeasurementUnitFactory.create(),
            measurement_unit_qualifier=factories.MeasurementUnitQualifierFactory.create(),
            update_type=UpdateType.CREATE,
        ),
        serializer=unit_serializers.MeasurementSerializer,
    )


def test_measurement_importer_update(update_imported_fields_match):
    assert update_imported_fields_match(
        factories.MeasurementFactory,
        serializers.MeasurementSerializer,
        dependencies={
            "measurement_unit": factories.MeasurementUnitFactory,
            "measurement_unit_qualifier": factories.MeasurementUnitQualifierFactory,
        },
    )


def test_monetary_unit_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.MonetaryUnitFactory,
        serializer=unit_serializers.MonetaryUnitSerializer,
    )


def test_monetary_unit_importer_update(update_imported_fields_match):
    assert update_imported_fields_match(
        factories.MonetaryUnitFactory, unit_serializers.MeasurementUnitSerializer
    )


def test_duty_expression_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.DutyExpressionFactory, serializers.DutyExpressionSerializer
    )


def test_duty_expression_importer_update(update_imported_fields_match):
    assert update_imported_fields_match(
        factories.DutyExpressionFactory, serializers.DutyExpressionSerializer
    )


def test_measure_type_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.MeasureTypeFactory.build(
            measure_type_series=factories.MeasureTypeSeriesFactory.create(),
            update_type=UpdateType.CREATE,
        ),
        serializers.MeasureTypeSerializer,
    )


def test_additional_code_type_measure_type_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.AdditionalCodeTypeMeasureTypeFactory.build(
            measure_type=factories.MeasureTypeFactory.create(),
            additional_code_type=factories.AdditionalCodeTypeFactory.create(),
            update_type=UpdateType.CREATE,
        ),
        serializers.AdditionalCodeTypeMeasureTypeSerializer,
    )


def test_measure_condition_code_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.MeasureConditionCodeFactory,
        serializers.MeasureConditionCodeSerializer,
    )


def test_measure_condition_code_importer_update(update_imported_fields_match):
    assert update_imported_fields_match(
        factories.MeasureConditionCodeFactory,
        serializers.MeasureConditionCodeSerializer,
    )


def test_measure_action_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.MeasureActionFactory, serializers.MeasureActionSerializer
    )


def test_measure_action_importer_update(update_imported_fields_match):
    assert update_imported_fields_match(
        factories.MeasureActionFactory, serializers.MeasureActionSerializer
    )


def test_measure_importer_create(
    imported_fields_match, approved_transaction, unapproved_transaction
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
        factories.MeasureFactory.build(
            measure_type=rel.measure_type,
            geographical_area=origin.geographical_area,
            goods_nomenclature=factories.GoodsNomenclatureFactory.create(
                item_id="7600000000"
            ),
            additional_code=ac,
            order_number=origin.order_number,
            generating_regulation=factories.RegulationFactory.create(),
            update_type=UpdateType.CREATE,
        ),
        serializers.MeasureSerializer,
    )


def test_measure_importer_update(
    update_imported_fields_match, approved_transaction, unapproved_transaction
):
    rel = factories.AdditionalCodeTypeMeasureTypeFactory.create(
        measure_type__order_number_capture_code=OrderNumberCaptureCode.MANDATORY,
    )
    origin = factories.QuotaOrderNumberOriginFactory.create(
        order_number__mechanism=AdministrationMechanism.FCFS,
        transaction=unapproved_transaction,
    )
    assert update_imported_fields_match(
        factories.MeasureFactory,
        serializers.MeasureSerializer,
        dependencies={
            "measure_type": rel.measure_type,
            "geographical_area": origin.geographical_area,
            "goods_nomenclature": factories.GoodsNomenclatureFactory,
            "additional_code": factories.AdditionalCodeFactory.create(
                type=rel.additional_code_type
            ),
            "order_number": origin.order_number,
            "generating_regulation": factories.RegulationFactory,
        },
    )


def test_measure_component_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.MeasureComponentFactory.build(
            component_measure=factories.MeasureFactory.create(),
            duty_expression=factories.DutyExpressionFactory.create(),
            monetary_unit=factories.MonetaryUnitFactory.create(),
            component_measurement=factories.MeasurementFactory.create(),
            update_type=UpdateType.CREATE,
        ),
        serializers.MeasureComponentSerializer,
    )


def test_measure_condition_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.MeasureConditionFactory.build(
            dependent_measure=factories.MeasureFactory.create(),
            condition_code=factories.MeasureConditionCodeFactory.create(),
            monetary_unit=factories.MonetaryUnitFactory.create(),
            condition_measurement=factories.MeasurementFactory.create(),
            action=factories.MeasureActionFactory.create(),
            required_certificate=factories.CertificateFactory.create(),
            update_type=UpdateType.CREATE,
        ),
        serializers.MeasureConditionSerializer,
    )


def test_measure_condition_component_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.MeasureConditionComponentFactory.build(
            condition=factories.MeasureConditionFactory.create(),
            duty_expression=factories.DutyExpressionFactory.create(),
            monetary_unit=factories.MonetaryUnitFactory.create(),
            condition_component_measurement=factories.MeasurementFactory.create(),
            update_type=UpdateType.CREATE,
        ),
        serializers.MeasureConditionComponentSerializer,
    )


def test_measure_excluded_geographical_area_importer_create(imported_fields_match):
    membership = factories.GeographicalMembershipFactory.create()

    assert imported_fields_match(
        factories.MeasureExcludedGeographicalAreaFactory.build(
            modified_measure=factories.MeasureFactory.create(
                geographical_area=membership.geo_group
            ),
            excluded_geographical_area=membership.member,
        ),
        serializers.MeasureExcludedGeographicalAreaSerializer,
    )


def test_measure_excluded_geographical_area_importer_update(
    update_imported_fields_match,
):
    membership = factories.GeographicalMembershipFactory.create()

    assert update_imported_fields_match(
        factories.MeasureExcludedGeographicalAreaFactory,
        serializers.MeasureExcludedGeographicalAreaSerializer,
        dependencies={
            "modified_measure": factories.MeasureFactory.create(
                geographical_area=membership.geo_group
            ),
            "excluded_geographical_area": membership.member,
        },
        validity=False,
    )


def test_footnote_association_measure_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.FootnoteAssociationMeasureFactory.build(
            footnoted_measure=factories.MeasureFactory.create(),
            associated_footnote=factories.FootnoteFactory.create(),
            update_type=UpdateType.CREATE,
        ),
        serializers.FootnoteAssociationMeasureSerializer,
    )
