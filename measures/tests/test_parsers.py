from decimal import Decimal
from typing import Dict
from typing import List
from typing import Tuple

import parsec  # type: ignore
import pytest

from common.models.trackedmodel import TrackedModel
from measures.models import MeasureComponent
from measures.models import MeasureConditionComponent
from measures.parsers import ConditionSentenceParser
from measures.parsers import DutySentenceParser
from measures.parsers import SeasonalRateParser

pytestmark = pytest.mark.django_db


def assert_attributes(expected, actual):
    if expected is None:
        assert actual is None
    else:
        assert actual is not None
        for field in expected:
            assert getattr(actual, field) == expected[field]


@pytest.fixture
def seasonal_rate_parser() -> SeasonalRateParser:
    return SeasonalRateParser()


@pytest.fixture
def condition_sentence_parser(
    duty_expressions,
    monetary_units,
    measurements,
    condition_codes,
    action_codes,
) -> ConditionSentenceParser:
    return ConditionSentenceParser(
        duty_expressions.values(),
        monetary_units.values(),
        measurements.values(),
        condition_codes.values(),
        action_codes.values(),
        2.00,
    )


@pytest.fixture
def get_condition_data(
    certificates,
    condition_codes,
    action_codes,
):
    def getter(
        condition_code,
        certificate_id,
        action_code,
    ):
        return {
            "condition_code": condition_codes.get(condition_code),
            "action": action_codes.get(action_code),
            "required_certificate": certificates.get(certificate_id),
        }

    return getter


def duty_sentence_parser_test(
    duty_sentence_parser: DutySentenceParser,
    duty_sentence_data: Tuple[str, List[Dict]],
    instance_class: TrackedModel,
):
    duty_sentence, expected_results = duty_sentence_data
    components = list(duty_sentence_parser.parse(duty_sentence))
    assert len(expected_results) == len(components)
    for expected, actual in zip(expected_results, components):
        assert_attributes(expected, actual)
        assert isinstance(actual, instance_class)


def test_reversible_duty_sentence_parsing(
    duty_sentence_parser: DutySentenceParser,
    reversible_duty_sentence_data,
):
    duty_sentence_parser_test(
        duty_sentence_parser,
        reversible_duty_sentence_data,
        MeasureComponent,
    )


def test_irreversible_duty_sentence_parsing(
    duty_sentence_parser: DutySentenceParser,
    irreversible_duty_sentence_data,
):
    duty_sentence_parser_test(
        duty_sentence_parser,
        irreversible_duty_sentence_data,
        MeasureComponent,
    )


def test_only_permitted_measurements_allowed(duty_sentence_parser):
    with pytest.raises(parsec.ParseError):
        duty_sentence_parser.parse("1.0 EUR / kg / lactic.")


def test_reversible_condition_duty_sentence_parsing(
    condition_duty_sentence_parser: DutySentenceParser,
    reversible_duty_sentence_data,
):
    duty_sentence_parser_test(
        condition_duty_sentence_parser,
        reversible_duty_sentence_data,
        MeasureConditionComponent,
    )


def test_irreversible_condition_duty_sentence_parsing(
    condition_duty_sentence_parser: DutySentenceParser,
    irreversible_duty_sentence_data,
):
    duty_sentence_parser_test(
        condition_duty_sentence_parser,
        irreversible_duty_sentence_data,
        MeasureConditionComponent,
    )


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


@pytest.fixture(
    params=(
        (
            "Cond: A cert: D-018 (01):0.000 GBP DTN Z; A (01):172.200 GBP DTN Z",
            [
                (("A", "D018", "01"), (1, Decimal("0.0"), "GBP", ("DTN", "Z"))),
                (("A", None, "01"), (1, Decimal("172.200"), "GBP", ("DTN", "Z"))),
            ],
        ),
        (
            "Cond: A cert: D-017 (01):0.000 % ; A cert: D-018 (01):28.200 % ; A (01):28.200 %",
            [
                (("A", "D017", "01"), (1, Decimal("0.00"), None, None)),
                (("A", "D018", "01"), (1, Decimal("28.2"), None, None)),
                (("A", None, "01"), (1, Decimal("28.2"), None, None)),
            ],
        ),
        (
            "Cond: A cert: D-017 (01):NIHIL",
            [
                (("A", "D017", "01"), (37, None, None, None)),
            ],
        ),
        (
            "Cond:  Y cert: D-017 (299):; Y cert: D-018 (299):; Y (09):",
            [
                (("Y", "D017", "299"), None),
                (("Y", "D018", "299"), None),
                (("Y", None, "09"), None),
            ],
        ),
        (
            "NIHIL",
            [
                (None, (37, None, None, None)),
            ],
        ),
        (
            "172.200 GBP DTN Z ",
            [
                (None, (1, Decimal("172.200"), "GBP", ("DTN", "Z"))),
            ],
        ),
        (
            "Cond: A cert: D-017 (01):10.000 EUR",
            [
                (("A", "D017", "01"), (1, Decimal("20.0"), "GBP", None)),
            ],
        ),
        (
            "Cond: A cert: D-017 (01):10.000 XEM",
            [
                (("A", "D017", "01"), (1, Decimal("10.0"), "XEM", None)),
            ],
        ),
        (
            "Cond: B cert: 9-100 (24):",
            [
                (("B", "9100", "24"), None),
            ],
        ),
    ),
)
def condition_sentence_data(request, get_condition_data, get_component_data):
    expected, expressions = request.param
    return expected, [
        (
            get_condition_data(*condition) if condition else None,
            get_component_data(*component) if component else None,
        )
        for (condition, component) in expressions
    ]


def test_condition_sentence_parsing(
    condition_sentence_parser: ConditionSentenceParser,
    condition_sentence_data,
):
    condition_sentence, expected_results = condition_sentence_data
    components = list(condition_sentence_parser.parse(condition_sentence))
    assert len(expected_results) == len(components)
    for expected, actual in zip(expected_results, components):
        expected_condition, expected_component = expected
        actual_condition, actual_component = actual
        assert_attributes(expected_condition, actual_condition)
        assert_attributes(expected_component, actual_component)
