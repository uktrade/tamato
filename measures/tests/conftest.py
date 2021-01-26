from typing import Sequence

import pytest
from django.core.exceptions import ValidationError

from common.tests import factories
from common.validators import ApplicabilityCode
from measures.models import DutyExpression
from measures.models import Measurement
from measures.models import MeasurementUnit
from measures.models import MeasurementUnitQualifier
from measures.models import MonetaryUnit
from measures.parsers import DutySentenceParser


@pytest.fixture
def component_applicability():
    def check(field_name, value, factory=None, applicability_field=None):
        if applicability_field is None:
            applicability_field = f"duty_expression__{field_name}_applicability_code"

        if factory is None:
            factory = factories.MeasureComponentFactory

        with pytest.raises(ValidationError):
            factory.create(
                **{
                    applicability_field: ApplicabilityCode.MANDATORY,
                    field_name: None,
                }
            )

        with pytest.raises(ValidationError):
            factory.create(
                **{
                    applicability_field: ApplicabilityCode.NOT_PERMITTED,
                    field_name: value,
                }
            )

        return True

    return check


@pytest.fixture
def percent_or_amount() -> DutyExpression:
    return factories.DutyExpressionFactory(
        sid=1,
        prefix="",
        duty_amount_applicability_code=ApplicabilityCode.MANDATORY,
        measurement_unit_applicability_code=ApplicabilityCode.PERMITTED,
        monetary_unit_applicability_code=ApplicabilityCode.PERMITTED,
    )


@pytest.fixture
def plus_percent_or_amount() -> DutyExpression:
    return factories.DutyExpressionFactory(
        sid=4,
        prefix="+",
        duty_amount_applicability_code=ApplicabilityCode.MANDATORY,
        measurement_unit_applicability_code=ApplicabilityCode.PERMITTED,
        monetary_unit_applicability_code=ApplicabilityCode.PERMITTED,
    )


@pytest.fixture
def plus_agri_component() -> DutyExpression:
    return factories.DutyExpressionFactory(
        sid=12,
        prefix="+ AC",
        duty_amount_applicability_code=ApplicabilityCode.NOT_PERMITTED,
        measurement_unit_applicability_code=ApplicabilityCode.PERMITTED,
        monetary_unit_applicability_code=ApplicabilityCode.PERMITTED,
    )


@pytest.fixture
def plus_amount_only() -> DutyExpression:
    return factories.DutyExpressionFactory(
        sid=20,
        prefix="+",
        duty_amount_applicability_code=ApplicabilityCode.MANDATORY,
        measurement_unit_applicability_code=ApplicabilityCode.MANDATORY,
        monetary_unit_applicability_code=ApplicabilityCode.MANDATORY,
    )


@pytest.fixture
def supplementary_unit() -> DutyExpression:
    return factories.DutyExpressionFactory(
        sid=99,
        prefix="",
        duty_amount_applicability_code=ApplicabilityCode.PERMITTED,
        measurement_unit_applicability_code=ApplicabilityCode.MANDATORY,
        monetary_unit_applicability_code=ApplicabilityCode.NOT_PERMITTED,
    )


@pytest.fixture
def duty_expressions(
    percent_or_amount: DutyExpression,
    plus_percent_or_amount: DutyExpression,
    plus_agri_component: DutyExpression,
    plus_amount_only: DutyExpression,
    supplementary_unit: DutyExpression,
) -> Sequence[DutyExpression]:
    return [
        percent_or_amount,
        plus_percent_or_amount,
        plus_agri_component,
        plus_amount_only,
        supplementary_unit,
    ]


@pytest.fixture
def monetary_units() -> Sequence[MonetaryUnit]:
    return [
        factories.MonetaryUnitFactory(code="EUR"),
        factories.MonetaryUnitFactory(code="GBP"),
        factories.MonetaryUnitFactory(code="XEM"),
    ]


@pytest.fixture
def measurement_units() -> Sequence[MeasurementUnit]:
    return [
        factories.MeasurementUnitFactory(code="KGM", abbreviation="kg"),
        factories.MeasurementUnitFactory(code="DTN", abbreviation="100 kg"),
        factories.MeasurementUnitFactory(code="MIL", abbreviation="1,000 p/st"),
    ]


@pytest.fixture
def unit_qualifiers() -> Sequence[MeasurementUnitQualifier]:
    return [
        factories.MeasurementUnitQualifierFactory(code="Z", abbreviation="lactic."),
    ]


@pytest.fixture
def measurements(measurement_units, unit_qualifiers) -> Sequence[Measurement]:
    return [
        *[
            factories.MeasurementFactory(
                measurement_unit=m, measurement_unit_qualifier=None
            )
            for m in measurement_units
        ],
        factories.MeasurementFactory(
            measurement_unit=measurement_units[1],
            measurement_unit_qualifier=unit_qualifiers[0],
        ),
    ]


@pytest.fixture
def duty_sentence_parser(
    duty_expressions,
    monetary_units,
    measurements,
) -> DutySentenceParser:
    return DutySentenceParser(
        duty_expressions,
        monetary_units,
        measurements,
    )
