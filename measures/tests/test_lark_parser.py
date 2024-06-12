from typing import Dict
from typing import List
from typing import Tuple

import pytest
from django.core.exceptions import ValidationError
from lark import Token

from measures.duty_sentence_parser import CompoundDutyNotPermitted
from measures.duty_sentence_parser import DutyAmountRequired
from measures.duty_sentence_parser import DutySentenceParser
from measures.duty_sentence_parser import InvalidDutyExpression
from measures.duty_sentence_parser import InvalidMeasurementUnit
from measures.duty_sentence_parser import InvalidMeasurementUnitQualififer
from measures.duty_sentence_parser import InvalidMonetaryUnit

pytestmark = pytest.mark.django_db

PERCENT_OR_AMOUNT_FIXTURE_NAME = "percent_or_amount"
PLUS_PERCENT_OR_AMOUNT_FIXTURE_NAME = "plus_percent_or_amount"
SUPPLEMENTARY_UNIT_FIXTURE_NAME = "supplementary_unit"
PLUS_AGRI_COMPONENT_FIXTURE_NAME = "plus_agri_component"
EURO_FIXTURE_NAME = "euro"
KILOGRAM_FIXTURE_NAME = "kilogram"
THOUSAND_ITEMS_FIXTURE_NAME = "thousand_items"
HECTOKILOGRAM_FIXTURE_NAME = "hectokilogram"
LACTIC_MATTER_FIXTURE_NAME = "lactic_matter"
ECU_CONVERSION_FIXTURE_NAME = "ecu_conversion"


@pytest.fixture(
    params=[
        (
            "4.000%",
            ["4.000", "%"],
            [{"duty_amount": 4.0, "duty_expression": PERCENT_OR_AMOUNT_FIXTURE_NAME}],
        ),
        (
            "1.230 EUR / kg",
            ["1.230", "EUR", "kg"],
            [
                {
                    "duty_amount": 1.23,
                    "duty_expression": PERCENT_OR_AMOUNT_FIXTURE_NAME,
                    "monetary_unit": EURO_FIXTURE_NAME,
                    "measurement_unit": KILOGRAM_FIXTURE_NAME,
                },
            ],
        ),
        (
            "0.300 XEM / 100 kg / lactic.",
            ["0.300", "XEM", "100 kg", "lactic."],
            [
                {
                    "duty_amount": 0.3,
                    "duty_expression": PERCENT_OR_AMOUNT_FIXTURE_NAME,
                    "measurement_unit": HECTOKILOGRAM_FIXTURE_NAME,
                    "measurement_unit_qualifier": LACTIC_MATTER_FIXTURE_NAME,
                    "monetary_unit": ECU_CONVERSION_FIXTURE_NAME,
                },
            ],
        ),
        (
            "12.900% + 20.000 EUR / kg",
            ["12.900", "%", "+", "20.000", "EUR", "kg"],
            [
                {
                    "duty_expression": PERCENT_OR_AMOUNT_FIXTURE_NAME,
                    "duty_amount": 12.9,
                },
                {
                    "duty_amount": 20.0,
                    "duty_expression": PLUS_PERCENT_OR_AMOUNT_FIXTURE_NAME,
                    "measurement_unit": KILOGRAM_FIXTURE_NAME,
                    "monetary_unit": EURO_FIXTURE_NAME,
                },
            ],
        ),
        (
            "kg",
            ["kg"],
            [
                {
                    "duty_expression": SUPPLEMENTARY_UNIT_FIXTURE_NAME,
                    "measurement_unit": KILOGRAM_FIXTURE_NAME,
                },
            ],
        ),
        (
            "100 kg",
            ["100 kg"],
            [
                {
                    "duty_expression": SUPPLEMENTARY_UNIT_FIXTURE_NAME,
                    "measurement_unit": HECTOKILOGRAM_FIXTURE_NAME,
                },
            ],
        ),
        (
            "1.000 EUR",
            ["1.000", "EUR"],
            [
                {
                    "duty_amount": 1.0,
                    "duty_expression": PERCENT_OR_AMOUNT_FIXTURE_NAME,
                    "monetary_unit": EURO_FIXTURE_NAME,
                },
            ],
        ),
        (
            "0.000% + AC",
            ["0.000", "%", "+ AC"],
            [
                {"duty_amount": 0.0, "duty_expression": PERCENT_OR_AMOUNT_FIXTURE_NAME},
                {"duty_expression": PLUS_AGRI_COMPONENT_FIXTURE_NAME},
            ],
        ),
    ],
    ids=[
        "simple_ad_valorem",
        "simple_specific_duty",
        "unit_with_qualifier",
        "multi_component_expression",
        "supplementary_unit",
        "supplementary_unit_with_numbers",
        "monetary_unit_without_measurement",
        "non_amount_expression",
    ],
)
def reversible_duty_sentence_data(request):
    """Duty sentence test cases that are syntactically correct and are also
    formatted correctly."""
    duty_sentence, exp_parsed, exp_transformed = request.param
    return duty_sentence, exp_parsed, exp_transformed


@pytest.fixture(
    params=[
        (
            f"20%+10EUR/100kg",
            ["20", "%", "+", "10", "EUR", "100kg"],
            [
                {
                    "duty_amount": 20.0,
                    "duty_expression": PERCENT_OR_AMOUNT_FIXTURE_NAME,
                },
                {
                    "duty_amount": 10.0,
                    "duty_expression": PLUS_PERCENT_OR_AMOUNT_FIXTURE_NAME,
                    "measurement_unit": HECTOKILOGRAM_FIXTURE_NAME,
                    "monetary_unit": EURO_FIXTURE_NAME,
                },
            ],
        ),
        (
            "20.0 EUR/100kg",
            ["20.0", "EUR", "100kg"],
            [
                {
                    "duty_amount": 20.0,
                    "duty_expression": PERCENT_OR_AMOUNT_FIXTURE_NAME,
                    "monetary_unit": EURO_FIXTURE_NAME,
                    "measurement_unit": HECTOKILOGRAM_FIXTURE_NAME,
                },
            ],
        ),
        (
            "1.0 EUR/1000 p/st",
            ["1.0", "EUR", "1000 p/st"],
            [
                {
                    "duty_amount": 1.0,
                    "duty_expression": PERCENT_OR_AMOUNT_FIXTURE_NAME,
                    "measurement_unit": THOUSAND_ITEMS_FIXTURE_NAME,
                    "monetary_unit": EURO_FIXTURE_NAME,
                },
            ],
        ),
    ],
    ids=[
        "parses_without_decimal_places",
        "parses_without_spaces",
        "parses_without_commas",
    ],
)
def irreversible_duty_sentence_data(request):
    """Duty sentence test cases that are syntactically correct but are not in
    the canonical rendering format with spaces and commas in the correct
    places."""
    duty_sentence, exp_parsed, exp_transformed = request.param
    return duty_sentence, exp_parsed, exp_transformed


def duty_sentence_parser_test(
    lark_duty_sentence_parser: DutySentenceParser,
    duty_sentence_data: Tuple[str, List[str], List[Dict]],
    request,
):
    duty_sentence, exp_parsed, exp_components = duty_sentence_data
    tree = lark_duty_sentence_parser.parse(duty_sentence)
    all_values = [
        token.value for token in tree.scan_values(lambda v: isinstance(v, Token))
    ]
    assert len(exp_parsed) == len(all_values)
    for expected, actual in zip(exp_parsed, all_values):
        assert expected == actual
    transformed = lark_duty_sentence_parser.transform(duty_sentence)
    assert len(transformed) == len(exp_components)
    for phrase, exp in zip(transformed, exp_components):
        with_fixtures = {
            key: request.getfixturevalue(val)
            for key, val in exp.items()
            if type(val) == str
        }
        exp.update(with_fixtures)
        assert phrase == exp


def test_reversible_duty_sentence_parsing(
    lark_duty_sentence_parser: DutySentenceParser,
    reversible_duty_sentence_data,
    request,
):
    duty_sentence_parser_test(
        lark_duty_sentence_parser,
        reversible_duty_sentence_data,
        request,
    )


def test_irreversible_duty_sentence_parsing(
    lark_duty_sentence_parser: DutySentenceParser,
    irreversible_duty_sentence_data,
    request,
):
    duty_sentence_parser_test(
        lark_duty_sentence_parser,
        irreversible_duty_sentence_data,
        request,
    )


def test_only_permitted_measurements_allowed(lark_duty_sentence_parser):
    with pytest.raises(ValidationError) as e:
        lark_duty_sentence_parser.transform("1.0 EUR / kg / lactic.")
        assert (
            e.message
            == "Measurement unit qualifier lactic. cannot be used with measurement unit kg."
        )


@pytest.mark.parametrize(
    "sentence, exp_error_class",
    [
        ("+", DutyAmountRequired),
        ("10% + Blah duty (reduced)", InvalidDutyExpression),
        ("5.5% + ABCDE + Some other fake duty expression", InvalidDutyExpression),
        ("10%&@#^&", InvalidDutyExpression),
        ("ABC", InvalidDutyExpression),
        ("@(*&$#)", InvalidDutyExpression),
        ("10% + 100 ABC / 100 kg", InvalidMonetaryUnit),
        ("100 DEF", InvalidMonetaryUnit),
        ("5.5% + 100 XYZ + AC (reduced)", InvalidMonetaryUnit),
        ("10% + 100 GBP / 100 abc", InvalidMeasurementUnit),
        ("100 GBP / foobar measurement", InvalidMeasurementUnit),
        ("5.5% + 100 EUR / foobar", InvalidMeasurementUnit),
        ("10% + 100 GBP / 100 kg / ABC", InvalidMeasurementUnitQualififer),
        ("100 GBP / 100 kg / XYZ foo bar", InvalidMeasurementUnitQualififer),
        ("5.5% + 100 EUR / kg / foo bar", InvalidMeasurementUnitQualififer),
    ],
)
def test_duty_syntax_errors(sentence, exp_error_class, lark_duty_sentence_parser):
    with pytest.raises(exp_error_class):
        lark_duty_sentence_parser.parse(sentence)


@pytest.mark.parametrize(
    "sentence",
    [
        "1% + 2 GBP / m3",
        "1% + AC (reduced)",
    ],
)
def test_compound_duty_not_permitted_error(sentence, simple_lark_duty_sentence_parser):
    """Tests that a parser not using the complete duty sentence grammar raises a
    `CompoundDutyNotPermitted` exception when parsing a compound duty."""
    with pytest.raises(CompoundDutyNotPermitted):
        simple_lark_duty_sentence_parser.parse(sentence)


@pytest.mark.parametrize(
    "sentence, exp_error_message",
    [
        (
            f"10% + 10% + 10% + 10% + 10% + 10%",
            "A duty expression cannot be used more than once in a duty sentence.",
        ),
        (
            f"+ 5.5% 10%",
            "Duty expressions must be used in the duty sentence in ascending order of SID.",
        ),
        (
            "+ AC 10%",
            f"Duty amount cannot be used with duty expression + agricultural component (+ AC).",
        ),
        (
            "NIHIL / 100 kg",
            f"Measurement unit 100 kg (KGM) cannot be used with duty expression (nothing) (NIHIL).",
        ),
    ],
)
def test_duty_validation_errors(sentence, exp_error_message, lark_duty_sentence_parser):
    """
    Tests validation based on applicability codes.

    See conftest.py for DutyExpression fixture details.
    """
    with pytest.raises(ValidationError) as e:
        lark_duty_sentence_parser.transform(sentence)
        assert exp_error_message in e.message
