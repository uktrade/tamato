from typing import Dict
from typing import List
from typing import Tuple

import pytest
from django.core.exceptions import ValidationError
from lark import Token

from measures.duty_sentence_parser import DutySentenceParser

pytestmark = pytest.mark.django_db


@pytest.fixture(
    params=(
        ("4.000%", ["4.000", "%"]),
        ("1.230 EUR / kg", ["1.230", "EUR", "kg"]),
        (
            "0.300 XEM / 100 kg / lactic.",
            ["0.300", "XEM", "100 kg", "lactic."],
        ),
        (
            "12.900% + 20.000 EUR / kg",
            ["12.900", "%", "+", "20.000", "EUR", "kg"],
        ),
        ("kg", ["kg"]),
        ("100 kg", ["100 kg"]),
        ("1.000 EUR", ["1.000", "EUR"]),
        ("0.000% + AC", ["0.000", "%", "+ AC"]),
    ),
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
    expected, component_data = request.param
    return expected, component_data


@pytest.fixture(
    params=(
        (f"20%+10EUR/100kg", ["20", "%", "+", "10", "EUR", "100kg"]),
        ("20.0 EUR/100kg", ["20.0", "EUR", "100kg"]),
        ("1.0 EUR/1000 p/st", ["1.0", "EUR", "1000 p/st"]),
    ),
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
    expected, component_data = request.param
    return expected, component_data


def duty_sentence_parser_test(
    lark_duty_sentence_parser: DutySentenceParser,
    duty_sentence_data: Tuple[str, List[Dict]],
):
    duty_sentence, expected_results = duty_sentence_data
    tree = lark_duty_sentence_parser.parse(duty_sentence)
    all_values = [
        token.value for token in tree.scan_values(lambda v: isinstance(v, Token))
    ]
    assert len(expected_results) == len(all_values)
    for expected, actual in zip(expected_results, all_values):
        assert expected == actual


def test_reversible_duty_sentence_parsing(
    lark_duty_sentence_parser: DutySentenceParser,
    reversible_duty_sentence_data,
):
    duty_sentence_parser_test(
        lark_duty_sentence_parser,
        reversible_duty_sentence_data,
    )


def test_irreversible_duty_sentence_parsing(
    lark_duty_sentence_parser: DutySentenceParser,
    irreversible_duty_sentence_data,
):
    duty_sentence_parser_test(
        lark_duty_sentence_parser,
        irreversible_duty_sentence_data,
    )


def test_only_permitted_measurements_allowed(lark_duty_sentence_parser):
    with pytest.raises(ValidationError) as e:
        lark_duty_sentence_parser.transform("1.0 EUR / kg / lactic.")
        assert (
            e.message
            == "Measurement unit qualifier lactic. cannot be used with measurement unit kg."
        )
