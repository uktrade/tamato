import pytest

from common.tests import factories
from common.tests.util import validate_taric_xml
from common.xml.namespaces import nsmap

pytestmark = pytest.mark.django_db


@validate_taric_xml(factories.AdditionalCodeTypeMeasureTypeFactory)
def test_additional_code_type_measure_type_xml(xml):
    assert xml.find(".//oub:additional.code.type.measure.type", nsmap) is not None


@validate_taric_xml(factories.DutyExpressionFactory)
def test_duty_expression_xml(xml):
    assert xml.find(".//oub:duty.expression", nsmap) is not None
    assert xml.find(".//oub:duty.expression.description", nsmap) is not None
    assert (
        xml.findtext(
            ".//oub:duty.expression.description/oub:language.id",
            namespaces=nsmap,
        )
        == "EN"
    )


@validate_taric_xml(factories.FootnoteAssociationMeasureFactory)
def test_footnote_association_measure_xml(xml):
    assert xml.find(".//oub:footnote.association.measure", nsmap) is not None


@validate_taric_xml(factories.MeasureWithQuotaFactory, check_order=False)
def test_measure_xml(xml):
    assert xml.find(".//oub:measure", nsmap) is not None


@validate_taric_xml(factories.MeasureActionFactory)
def test_measure_action_xml(xml):
    assert xml.find(".//oub:measure.action", nsmap) is not None
    assert xml.find(".//oub:measure.action.description", nsmap) is not None
    assert (
        xml.findtext(
            ".//oub:measure.action.description/oub:language.id",
            namespaces=nsmap,
        )
        == "EN"
    )


@validate_taric_xml(factories.MeasureComponentFactory)
def test_measure_component_xml(xml):
    assert xml.find(".//oub:measure.component", nsmap) is not None


@validate_taric_xml(factories.MeasureConditionFactory)
def test_measure_condition_xml(xml):
    assert xml.find(".//oub:measure.condition", nsmap) is not None


@validate_taric_xml(factories.MeasureConditionCodeFactory)
def test_measure_condition_code_xml(xml):
    assert xml.find(".//oub:measure.condition.code", nsmap) is not None
    assert xml.find(".//oub:measure.condition.code.description", nsmap) is not None
    assert (
        xml.findtext(
            ".//oub:measure.condition.code.description/oub:language.id",
            namespaces=nsmap,
        )
        == "EN"
    )


@validate_taric_xml(factories.MeasureConditionComponentFactory)
def test_measure_condition_component_xml(xml):
    assert xml.find(".//oub:measure.condition.component", nsmap) is not None


@validate_taric_xml(factories.MeasureExcludedGeographicalMembershipFactory)
def test_measure_excluded_geographical_area_xml(xml):
    assert xml.find(".//oub:measure.excluded.geographical.area", nsmap) is not None


@validate_taric_xml(factories.MeasureTypeFactory)
def test_measure_type_xml(xml):
    assert xml.find(".//oub:measure.type", nsmap) is not None
    assert xml.find(".//oub:measure.type.description", nsmap) is not None
    assert (
        xml.findtext(
            ".//oub:measure.type.description/oub:language.id",
            namespaces=nsmap,
        )
        == "EN"
    )


@validate_taric_xml(factories.MeasureTypeSeriesFactory)
def test_measure_type_series_xml(xml):
    assert xml.find(".//oub:measure.type.series", nsmap) is not None
    assert xml.find(".//oub:measure.type.series.description", nsmap) is not None
    assert (
        xml.findtext(
            ".//oub:measure.type.series.description/oub:language.id",
            namespaces=nsmap,
        )
        == "EN"
    )


@validate_taric_xml(factories.MeasurementFactory)
def test_measurement_xml(xml):
    assert xml.find(".//oub:measurement", nsmap) is not None


@validate_taric_xml(factories.MeasurementUnitFactory)
def test_measurement_unit_xml(xml):
    assert xml.find(".//oub:measurement.unit", nsmap) is not None
    assert xml.find(".//oub:measurement.unit.description", nsmap) is not None
    assert (
        xml.findtext(
            ".//oub:measurement.unit.description/oub:language.id",
            namespaces=nsmap,
        )
        == "EN"
    )


@validate_taric_xml(factories.MeasurementUnitQualifierFactory)
def test_measurement_unit_qualifier_xml(xml):
    assert xml.find(".//oub:measurement.unit.qualifier", nsmap) is not None
    assert xml.find(".//oub:measurement.unit.qualifier.description", nsmap) is not None
    assert (
        xml.findtext(
            ".//oub:measurement.unit.qualifier.description/oub:language.id",
            namespaces=nsmap,
        )
        == "EN"
    )


@validate_taric_xml(factories.MonetaryUnitFactory)
def test_monetary_unit_xml(xml):
    assert xml.find(".//oub:monetary.unit", nsmap) is not None
    assert xml.find(".//oub:monetary.unit.description", nsmap) is not None
    assert (
        xml.findtext(
            ".//oub:monetary.unit.description/oub:language.id",
            namespaces=nsmap,
        )
        == "EN"
    )
