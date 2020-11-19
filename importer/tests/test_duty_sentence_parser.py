import parsec  # type: ignore
import pytest

from common.validators import ApplicabilityCode
from importer.duty_sentence_parser import DutySentenceParser
from measures.models import DutyExpression
from measures.models import Measurement
from measures.models import MeasurementUnit
from measures.models import MeasurementUnitQualifier
from measures.models import MonetaryUnit

PERCENT_OR_AMOUNT = DutyExpression(
    sid=1,
    prefix="",
    duty_amount_applicability_code=ApplicabilityCode.MANDATORY,
    measurement_unit_applicability_code=ApplicabilityCode.PERMITTED,
    monetary_unit_applicability_code=ApplicabilityCode.PERMITTED,
)
PLUS_PERCENT_OR_AMOUNT = DutyExpression(
    sid=2,
    prefix="+",
    duty_amount_applicability_code=ApplicabilityCode.MANDATORY,
    measurement_unit_applicability_code=ApplicabilityCode.PERMITTED,
    monetary_unit_applicability_code=ApplicabilityCode.PERMITTED,
)
PLUS_AGRI_COMPONENT = DutyExpression(
    sid=12,
    prefix="+ AC",
    duty_amount_applicability_code=ApplicabilityCode.NOT_PERMITTED,
    measurement_unit_applicability_code=ApplicabilityCode.PERMITTED,
    monetary_unit_applicability_code=ApplicabilityCode.PERMITTED,
)
PLUS_AMOUNT_ONLY = DutyExpression(
    sid=20,
    prefix="+",
    duty_amount_applicability_code=ApplicabilityCode.MANDATORY,
    measurement_unit_applicability_code=ApplicabilityCode.MANDATORY,
    monetary_unit_applicability_code=ApplicabilityCode.MANDATORY,
)
SUPPLEMENTARY_UNIT = DutyExpression(
    sid=99,
    prefix="",
    duty_amount_applicability_code=ApplicabilityCode.PERMITTED,
    measurement_unit_applicability_code=ApplicabilityCode.MANDATORY,
    monetary_unit_applicability_code=ApplicabilityCode.NOT_PERMITTED,
)

DUTY_EXPRESSIONS = [
    PERCENT_OR_AMOUNT,
    PLUS_PERCENT_OR_AMOUNT,
    PLUS_AGRI_COMPONENT,
    PLUS_AMOUNT_ONLY,
    SUPPLEMENTARY_UNIT,
]

MONETARY_UNITS = [
    MonetaryUnit(code="EUR"),
    MonetaryUnit(code="GBP"),
    MonetaryUnit(code="XEM"),
]

MEASUREMENT_UNITS = [
    MeasurementUnit(code="KGM", abbreviation="kg"),
    MeasurementUnit(code="DTN", abbreviation="100 kg"),
    MeasurementUnit(code="MIL", abbreviation="1,000 p/st"),
]

UNIT_QUALIFIERS = [
    MeasurementUnitQualifier(code="Z", abbreviation="lactic."),
]

MEASUREMENTS = [
    *[Measurement(measurement_unit=m) for m in MEASUREMENT_UNITS],
    Measurement(
        measurement_unit=MEASUREMENT_UNITS[1],
        measurement_unit_qualifier=UNIT_QUALIFIERS[0],
    ),
]

parser = DutySentenceParser(
    DUTY_EXPRESSIONS,
    MONETARY_UNITS,
    MEASUREMENTS,
)

parser.measurement_parser.parse_strict("100 kg / lactic.")


def get_from_field(value, options, field=lambda e: e.code):
    matches = list(filter(lambda unit: field(unit) == value, options))
    return matches[0] if len(matches) > 0 else None


def assert_parses(string, *expecteds):
    components = parser.parse(string)
    assert len(expecteds) == len(components)
    for expected, actual in zip(expecteds, components):
        expected_duty_expression = get_from_field(
            expected[0], DUTY_EXPRESSIONS, lambda e: e.sid
        )
        expected_monetary_unit = get_from_field(expected[2], MONETARY_UNITS)
        expected_measurement = get_from_field(
            expected[3],
            MEASUREMENTS,
            lambda e: (
                e.measurement_unit.code,
                e.measurement_unit_qualifier.code
                if e.measurement_unit_qualifier
                else None,
            ),
        )

        assert actual.duty_expression == expected_duty_expression
        assert actual.duty_amount == expected[1]
        assert actual.monetary_unit == expected_monetary_unit
        assert actual.component_measurement == expected_measurement


def test_simple_ad_vaolrem():
    assert_parses("4.0%", (1, 4.0, None, None))


def test_simple_specific_duty():
    assert_parses("1.23 EUR/kg", (1, 1.23, "EUR", ("KGM", None)))


def test_unit_with_qualifier():
    assert_parses("0.30 XEM / 100 kg / lactic.", (1, 0.3, "XEM", ("DTN", "Z")))


def test_multi_component_expression():
    assert_parses(
        "6.00% + 3.50 GBP / 100 kg", (1, 12.9, None, None), (2, 20.0, "EUR", ("KGM", None))
    )


def test_supplementary_unit():
    assert_parses("kg", (99, None, None, ("KGM", None)))


def test_supplementary_unit_with_numbers():
    assert_parses("100 kg", (99, None, None, ("DTN", None)))


def test_monetary_unit_without_measurement():
    assert_parses("1.0 EUR", (1, 1.0, "EUR", None))


def test_non_amount_expression():
    assert_parses("0.0% + AC", (1, 0.0, None, None), (12, None, None, None))


def test_only_permitted_measurements_allowed():
    with pytest.raises(parsec.ParseError):
        parser.parse("1.0 EUR / kg / lactic.")


def test_parses_without_spaces():
    assert_parses("20.0 EUR/100kg", (1, 20.0, "EUR", ("DTN", None)))


def test_parses_without_commas():
    assert_parses("1.0 EUR/1000 p/st", (1, 1.0, "EUR", ("MIL", None)))
