import pytest

from common.tests import factories
from common.tests.util import validate_taric_xml

pytestmark = pytest.mark.django_db


@validate_taric_xml(factories.AdditionalCodeTypeMeasureTypeFactory)
def test_additional_code_type_measure_type_xml(api, schema, xml):
    assert xml.find(".//additional.code.type.measure.type", xml.nsmap) is not None


@validate_taric_xml(factories.DutyExpressionFactory)
def test_duty_expression_xml(api, schema, xml):
    assert xml.find(".//duty.expression", xml.nsmap) is not None
    assert xml.find(".//duty.expression.description", xml.nsmap) is not None
    assert (
        xml.findtext(".//duty.expression.description/language.id", namespaces=xml.nsmap)
        == "EN"
    )


@validate_taric_xml(factories.FootnoteAssociationMeasureFactory)
def test_footnote_association_measure_xml(api, schema, xml):
    assert xml.find(".//footnote.association.measure", xml.nsmap) is not None


@validate_taric_xml(factories.MeasureWithQuotaFactory, check_order=False)
def test_measure_xml(api, schema, xml):
    assert xml.find(".//measure", xml.nsmap) is not None


@validate_taric_xml(factories.MeasureActionFactory)
def test_measure_action_xml(api, schema, xml):
    assert xml.find(".//measure.action", xml.nsmap) is not None
    assert xml.find(".//measure.action.description", xml.nsmap) is not None
    assert (
        xml.findtext(".//measure.action.description/language.id", namespaces=xml.nsmap)
        == "EN"
    )


@validate_taric_xml(factories.MeasureComponentFactory)
def test_measure_component_xml(api, schema, xml):
    assert xml.find(".//measure.component", xml.nsmap) is not None


@validate_taric_xml(factories.MeasureConditionFactory)
def test_measure_condition_xml(api, schema, xml):
    assert xml.find(".//measure.condition", xml.nsmap) is not None


@validate_taric_xml(factories.MeasureConditionCodeFactory)
def test_measure_condition_code_xml(api, schema, xml):
    assert xml.find(".//measure.condition.code", xml.nsmap) is not None
    assert xml.find(".//measure.condition.code.description", xml.nsmap) is not None
    assert (
        xml.findtext(
            ".//measure.condition.code.description/language.id", namespaces=xml.nsmap
        )
        == "EN"
    )


@validate_taric_xml(factories.MeasureConditionComponentFactory)
def test_measure_condition_component_xml(api, schema, xml):
    assert xml.find(".//measure.condition.component", xml.nsmap) is not None


@validate_taric_xml(factories.MeasureExcludedGeographicalMembershipFactory)
def test_measure_excluded_geographical_area_xml(api, schema, xml):
    assert xml.find(".//measure.excluded.geographical.area", xml.nsmap) is not None


@validate_taric_xml(factories.MeasureTypeFactory)
def test_measure_type_xml(api, schema, xml):
    assert xml.find(".//measure.type", xml.nsmap) is not None
    assert xml.find(".//measure.type.description", xml.nsmap) is not None
    assert (
        xml.findtext(".//measure.type.description/language.id", namespaces=xml.nsmap)
        == "EN"
    )


@validate_taric_xml(factories.MeasureTypeSeriesFactory)
def test_measure_type_series_xml(api, schema, xml):
    assert xml.find(".//measure.type.series", xml.nsmap) is not None
    assert xml.find(".//measure.type.series.description", xml.nsmap) is not None
    assert (
        xml.findtext(
            ".//measure.type.series.description/language.id", namespaces=xml.nsmap
        )
        == "EN"
    )


@validate_taric_xml(factories.MeasurementFactory)
def test_measurement_xml(api, schema, xml):
    assert xml.find(".//measurement", xml.nsmap) is not None


@validate_taric_xml(factories.MeasurementUnitFactory)
def test_measurement_unit_xml(api, schema, xml):
    assert xml.find(".//measurement.unit", xml.nsmap) is not None
    assert xml.find(".//measurement.unit.description", xml.nsmap) is not None
    assert (
        xml.findtext(
            ".//measurement.unit.description/language.id", namespaces=xml.nsmap
        )
        == "EN"
    )


@validate_taric_xml(factories.MeasurementUnitQualifierFactory)
def test_measurement_unit_qualifier_xml(api, schema, xml):
    assert xml.find(".//measurement.unit.qualifier", xml.nsmap) is not None
    assert xml.find(".//measurement.unit.qualifier.description", xml.nsmap) is not None
    assert (
        xml.findtext(
            ".//measurement.unit.qualifier.description/language.id",
            namespaces=xml.nsmap,
        )
        == "EN"
    )


@validate_taric_xml(factories.MonetaryUnitFactory)
def test_monetary_unit_xml(api, schema, xml):
    assert xml.find(".//monetary.unit", xml.nsmap) is not None
    assert xml.find(".//monetary.unit.description", xml.nsmap) is not None
    assert (
        xml.findtext(".//monetary.unit.description/language.id", namespaces=xml.nsmap)
        == "EN"
    )
