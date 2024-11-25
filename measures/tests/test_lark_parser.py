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
from measures.models import DutyExpression
from measures.validators import ApplicabilityCode

pytestmark = pytest.mark.django_db

PERCENT_OR_AMOUNT_FIXTURE_NAME = "percent_or_amount"
PLUS_PERCENT_OR_AMOUNT_SID = (4, 19, 20)
SUPPLEMENTARY_UNIT_FIXTURE_NAME = "supplementary_unit"
PLUS_AGRI_COMPONENT_FIXTURE_NAME = "plus_agri_component"
MAXIMUM_SID = (17, 35)
NOTHING_FIXTURE_NAME = "nothing"
BRITISH_POUND_FIXTURE_NAME = "british_pound"
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
            "9.10% MAX 1.00% + 0.90 GBP / 100 kg",
            ["9.10", "%", "MAX", "1.00", "%", "+", "0.90", "GBP", "100 kg"],
            [
                {
                    "duty_amount": 9.1,
                    "duty_expression": PERCENT_OR_AMOUNT_FIXTURE_NAME,
                },
                {
                    "duty_expression_sid": MAXIMUM_SID[0],
                    "duty_amount": 1.0,
                },
                {
                    "duty_expression_sid": PLUS_PERCENT_OR_AMOUNT_SID[1],
                    "duty_amount": 0.9,
                    "monetary_unit": BRITISH_POUND_FIXTURE_NAME,
                    "measurement_unit": HECTOKILOGRAM_FIXTURE_NAME,
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
                    "duty_expression_sid": PLUS_PERCENT_OR_AMOUNT_SID[0],
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
        "max_compound_duty",
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
                    "duty_expression_sid": PLUS_PERCENT_OR_AMOUNT_SID[0],
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


def replace_with_component_instances(expected_components: dict, request) -> None:
    """
    Modifies `expected_components` so that it can be compared to a dictionary of
    parsed and transformed duty components.

    Duty component fixture names and duty expression SID values are replaced
    with their object instances.
    """
    if "duty_expression_sid" in expected_components:
        expected_components["duty_expression"] = DutyExpression.objects.get(
            sid=expected_components["duty_expression_sid"],
        )
        expected_components.pop("duty_expression_sid")

    with_fixtures = {
        key: request.getfixturevalue(val)
        for key, val in expected_components.items()
        if type(val) == str
    }
    expected_components.update(with_fixtures)


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
        replace_with_component_instances(exp, request)
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
        "Measurement unit qualifier lactic. cannot be used with measurement unit kg."
        in str(e.value)
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
    """Tests that a parser with `compound_duties` set to `False` raises a
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
            f"+ AC 10%",
            "Duty expressions must be used in the duty sentence in ascending order of SID.",
        ),
        (
            "NIHIL / 100 kg",
            f"Measurement unit 100 kg (DTN) cannot be used with duty expression (nothing) (NIHIL).",
        ),
    ],
)
def test_duty_transformer_duty_expression_validation_errors(
    sentence,
    exp_error_message,
    lark_duty_sentence_parser,
):
    with pytest.raises(ValidationError) as error:
        lark_duty_sentence_parser.transform(sentence)
    assert exp_error_message in str(error.value)


@pytest.mark.parametrize(
    "code, duty_expression, item, item_name, error_message",
    [
        (
            ApplicabilityCode.NOT_PERMITTED,
            PLUS_AGRI_COMPONENT_FIXTURE_NAME,
            10.0,
            "duty amount",
            "Duty amount cannot be used with duty expression + agricultural component (+ AC).",
        ),
        (
            ApplicabilityCode.NOT_PERMITTED,
            NOTHING_FIXTURE_NAME,
            BRITISH_POUND_FIXTURE_NAME,
            "monetary unit",
            "Monetary unit cannot be used with duty expression (nothing) (NIHIL).",
        ),
        (
            ApplicabilityCode.MANDATORY,
            PERCENT_OR_AMOUNT_FIXTURE_NAME,
            None,
            "duty amount",
            f"Duty expression % or amount () requires a duty amount.",
        ),
    ],
)
def test_duty_transformer_applicability_code_validation_errors(
    code,
    duty_expression,
    item,
    item_name,
    error_message,
    lark_duty_sentence_parser,
    request,
):
    with pytest.raises(ValidationError) as error:
        transformer = lark_duty_sentence_parser.transformer
        duty_expression = request.getfixturevalue(duty_expression)
        transformer.validate_according_to_applicability_code(
            code,
            duty_expression,
            item,
            item_name,
        )
    assert error_message in str(error.value)
