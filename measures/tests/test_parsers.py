from typing import Dict
from typing import List
from typing import Tuple

import parsec  # type: ignore
import pytest

from measures.parsers import DutySentenceParser
from measures.parsers import SeasonalRateParser

pytestmark = pytest.mark.django_db


@pytest.fixture
def seasonal_rate_parser() -> SeasonalRateParser:
    return SeasonalRateParser()


def duty_sentence_parser_test(
    duty_sentence_parser: DutySentenceParser,
    duty_sentence_data: Tuple[str, List[Dict]],
):
    duty_sentence, expected_results = duty_sentence_data
    components = list(duty_sentence_parser.parse(duty_sentence))
    assert len(expected_results) == len(components)
    for expected, actual in zip(expected_results, components):
        for field in expected:
            assert getattr(actual, field) == expected[field]


def test_reversible_duty_sentence_parsing(
    duty_sentence_parser: DutySentenceParser,
    reversible_duty_sentence_data,
):
    duty_sentence_parser_test(duty_sentence_parser, reversible_duty_sentence_data)


def test_irreversible_duty_sentence_parsing(
    duty_sentence_parser: DutySentenceParser,
    irreversible_duty_sentence_data,
):
    duty_sentence_parser_test(duty_sentence_parser, irreversible_duty_sentence_data)


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
