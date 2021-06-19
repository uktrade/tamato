import pytest

from common.tests import factories
from measures.validators import OrderNumberCaptureCode
from quotas.validators import AdministrationMechanism

pytestmark = pytest.mark.django_db


def test_measure_type_series_importer(imported_fields_match):
    assert imported_fields_match(
        factories.MeasureTypeSeriesFactory,
    )


def test_measurement_unit_importer(imported_fields_match):
    assert imported_fields_match(
        factories.MeasurementUnitFactory,
    )


def test_measurement_unit_qualifier_importer(imported_fields_match):
    assert imported_fields_match(
        factories.MeasurementUnitQualifierFactory,
    )


def test_measurement_importer(imported_fields_match):
    assert imported_fields_match(
        factories.MeasurementFactory,
        dependencies={
            "measurement_unit": factories.MeasurementUnitFactory,
            "measurement_unit_qualifier": factories.MeasurementUnitQualifierFactory,
        },
    )


def test_monetary_unit_importer(imported_fields_match):
    assert imported_fields_match(
        factories.MonetaryUnitFactory,
    )


def test_duty_expression_importer(imported_fields_match):
    assert imported_fields_match(
        factories.DutyExpressionFactory,
    )


def test_measure_type_importer(imported_fields_match):
    assert imported_fields_match(
        factories.MeasureTypeFactory,
        dependencies={
            "measure_type_series": factories.MeasureTypeSeriesFactory,
        },
    )


def test_additional_code_type_measure_type_importer(imported_fields_match):
    assert imported_fields_match(
        factories.AdditionalCodeTypeMeasureTypeFactory,
        dependencies={
            "measure_type": factories.MeasureTypeFactory,
            "additional_code_type": factories.AdditionalCodeTypeFactory,
        },
    )


def test_measure_condition_code_importer(imported_fields_match):
    assert imported_fields_match(
        factories.MeasureConditionCodeFactory,
    )


def test_measure_action_importer(imported_fields_match):
    assert imported_fields_match(
        factories.MeasureActionFactory,
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
        dependencies={
            "footnoted_measure": factories.MeasureFactory,
            "associated_footnote": factories.FootnoteFactory,
        },
    )
