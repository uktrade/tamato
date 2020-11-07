import pytest

from common.tests import factories
from common.validators import UpdateType
from measures import unit_serializers
from measures.validators import OrderNumberCaptureCode
from quotas.validators import AdministrationMechanism
from workbaskets.validators import WorkflowStatus


pytestmark = pytest.mark.django_db


def test_measure_type_series_importer_create(imported_fields_match):
    assert imported_fields_match(factories.MeasureTypeSeriesFactory)


def test_measurement_unit_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.MeasurementUnitFactory,
        serializer=unit_serializers.MeasurementUnitSerializer,
    )


def test_measurement_unit_qualifier_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.MeasurementUnitQualifierFactory,
        serializer=unit_serializers.MeasurementUnitQualifierSerializer,
    )


def test_measurement_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.MeasurementFactory.build(
            measurement_unit=factories.MeasurementUnitFactory(),
            measurement_unit_qualifier=factories.MeasurementUnitQualifierFactory(),
            update_type=UpdateType.CREATE,
        ),
        serializer=unit_serializers.MeasurementSerializer,
    )


def test_monetary_unit_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.MonetaryUnitFactory,
        serializer=unit_serializers.MonetaryUnitSerializer,
    )


def test_duty_expression_importer_create(imported_fields_match):
    assert imported_fields_match(factories.DutyExpressionFactory)


def test_measure_type_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.MeasureTypeFactory.build(
            measure_type_series=factories.MeasureTypeSeriesFactory(),
            update_type=UpdateType.CREATE,
        )
    )


def test_additional_code_type_measure_type_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.AdditionalCodeTypeMeasureTypeFactory.build(
            measure_type=factories.MeasureTypeFactory(),
            additional_code_type=factories.AdditionalCodeTypeFactory(),
            update_type=UpdateType.CREATE,
        )
    )


def test_measure_condition_code_importer_create(imported_fields_match):
    assert imported_fields_match(factories.MeasureConditionCodeFactory)


def test_measure_action_importer_create(imported_fields_match):
    assert imported_fields_match(factories.MeasureActionFactory)


def test_measure_importer_create(imported_fields_match):
    rel = factories.AdditionalCodeTypeMeasureTypeFactory(
        measure_type__order_number_capture_code=OrderNumberCaptureCode.MANDATORY,
    )
    origin = factories.QuotaOrderNumberOriginFactory(
        order_number__mechanism=AdministrationMechanism.FCFS,
        workbasket=factories.WorkBasketFactory(
            pk=999,
            status=WorkflowStatus.READY_FOR_EXPORT,
            approver=factories.UserFactory(),
        ),
    )

    assert imported_fields_match(
        factories.MeasureFactory.build(
            measure_type=rel.measure_type,
            geographical_area=origin.geographical_area,
            goods_nomenclature=factories.GoodsNomenclatureFactory(),
            additional_code=factories.AdditionalCodeFactory(
                type=rel.additional_code_type
            ),
            order_number=origin.order_number,
            generating_regulation=factories.RegulationFactory(),
            update_type=UpdateType.CREATE,
        )
    )


def test_measure_component_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.MeasureComponentFactory.build(
            component_measure=factories.MeasureFactory(),
            duty_expression=factories.DutyExpressionFactory(),
            monetary_unit=factories.MonetaryUnitFactory(),
            component_measurement=factories.MeasurementFactory(),
            update_type=UpdateType.CREATE,
        )
    )


def test_measure_condition_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.MeasureConditionFactory.build(
            dependent_measure=factories.MeasureFactory(),
            condition_code=factories.MeasureConditionCodeFactory(),
            monetary_unit=factories.MonetaryUnitFactory(),
            condition_measurement=factories.MeasurementFactory(),
            action=factories.MeasureActionFactory(),
            required_certificate=factories.CertificateFactory(),
            update_type=UpdateType.CREATE,
        )
    )


def test_measure_condition_component_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.MeasureConditionComponentFactory.build(
            condition=factories.MeasureConditionFactory(),
            duty_expression=factories.DutyExpressionFactory(),
            monetary_unit=factories.MonetaryUnitFactory(),
            condition_component_measurement=factories.MeasurementFactory(),
            update_type=UpdateType.CREATE,
        )
    )


def test_measure_excluded_geographical_area_importer_create(imported_fields_match):
    membership = factories.GeographicalMembershipFactory()

    assert imported_fields_match(
        factories.MeasureExcludedGeographicalAreaFactory.build(
            modified_measure=factories.MeasureFactory(
                geographical_area=membership.geo_group
            ),
            excluded_geographical_area=membership.member,
            update_type=UpdateType.CREATE,
        )
    )


def test_footnote_association_measure_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.FootnoteAssociationMeasureFactory.build(
            footnoted_measure=factories.MeasureFactory(),
            associated_footnote=factories.FootnoteFactory(),
            update_type=UpdateType.CREATE,
        )
    )
