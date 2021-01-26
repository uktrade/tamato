from typing import Sequence

import parsec  # type: ignore
import pytest

from measures.models import DutyExpression
from measures.models import Measurement
from measures.models import MonetaryUnit
from measures.parsers import DutySentenceParser
from measures.parsers import SeasonalRateParser

pytestmark = pytest.mark.django_db


@pytest.fixture
def seasonal_rate_parser() -> SeasonalRateParser:
    return SeasonalRateParser()


@pytest.mark.parametrize(
    "duty_sentence, expected_results",
    [
        ("4.0%", [(1, 4.0, None, None)]),
        ("1.23 EUR/kg", [(1, 1.23, "EUR", ("KGM", None))]),
        ("0.30 XEM / 100 kg / lactic.", [(1, 0.3, "XEM", ("DTN", "Z"))]),
        (
            "12.9 % + 20.0 EUR/kg",
            [(1, 12.9, None, None), (4, 20.0, "EUR", ("KGM", None))],
        ),
        ("kg", [(99, None, None, ("KGM", None))]),
        ("100 kg", [(99, None, None, ("DTN", None))]),
        ("1.0 EUR", [(1, 1.0, "EUR", None)]),
        ("0.0% + AC", [(1, 0.0, None, None), (12, None, None, None)]),
        ("20.0 EUR/100kg", [(1, 20.0, "EUR", ("DTN", None))]),
        ("1.0 EUR/1000 p/st", [(1, 1.0, "EUR", ("MIL", None))]),
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
        "parses_without_spaces",
        "parses_without_commas",
    ],
)
def test_duty_sentence_parser(
    duty_sentence_parser: DutySentenceParser,
    duty_expressions: Sequence[DutyExpression],
    monetary_units: Sequence[MonetaryUnit],
    measurements: Sequence[Measurement],
    duty_sentence: str,
    expected_results,
):
    def get_from_field(value, options, field=lambda e: e.code):
        matches = list(filter(lambda unit: field(unit) == value, options))
        return matches[0] if len(matches) > 0 else None

    components = list(duty_sentence_parser.parse(duty_sentence))
    assert len(expected_results) == len(components)
    for expected, actual in zip(expected_results, components):
        expected_duty_expression = get_from_field(
            expected[0], duty_expressions, lambda e: e.sid
        )
        expected_monetary_unit = get_from_field(expected[2], monetary_units)
        expected_measurement = get_from_field(
            expected[3],
            measurements,
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


def test_only_permitted_measurements_allowed(duty_sentence_parser):
    with pytest.raises(parsec.ParseError):
        duty_sentence_parser.parse("1.0 EUR / kg / lactic.")


@pytest.mark.parametrize(
    "duty_sentence, expected_results",
    [
        ("0.0%", []),
        ("4.0% (12 JAN - 13 MAR)", [("4.0%", 12, 1, 13, 3)]),
        (
            "16.1% (15 JAN - 06 JUL); 12.5% (03 OCT - 29 NOV);",
            [("16.1%", 15, 1, 6, 7), ("12.5%", 3, 10, 29, 11)],
        ),
        ("2.0% (25 NOV - 25 JAN)", [("2.0%", 25, 11, 25, 1)]),
    ],
    ids=[
        "rate_with_no_seasons",
        "rate_with_one_season",
        "rate_with_multiple_seasons",
        "rate_with_season_over_year_end",
    ],
)
def test_seasonal_rate_parser(
    seasonal_rate_parser: SeasonalRateParser,
    duty_sentence: str,
    expected_results,
):
    for index, season in enumerate(seasonal_rate_parser.detect_seasons(duty_sentence)):
        assert expected_results[index] == season
