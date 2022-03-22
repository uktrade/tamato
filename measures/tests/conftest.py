import datetime
from typing import Callable
from typing import Dict
from typing import Optional
from typing import Sequence
from typing import Tuple

import pytest
import requests
from django.core.exceptions import ValidationError
from django.forms.models import model_to_dict

from common.tests import factories
from common.util import TaricDateRange
from common.validators import ApplicabilityCode
from measures.forms import MeasureForm
from measures.models import DutyExpression
from measures.models import Measure
from measures.models import MeasureAction
from measures.models import MeasureConditionCode
from measures.models import MeasureConditionComponent
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
def nothing() -> DutyExpression:
    return factories.DutyExpressionFactory(
        sid=37,
        prefix="NIHIL",
        duty_amount_applicability_code=ApplicabilityCode.NOT_PERMITTED,
        measurement_unit_applicability_code=ApplicabilityCode.NOT_PERMITTED,
        monetary_unit_applicability_code=ApplicabilityCode.NOT_PERMITTED,
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
    nothing: DutyExpression,
) -> Dict[int, DutyExpression]:
    return {
        d.sid: d
        for d in [
            percent_or_amount,
            plus_percent_or_amount,
            plus_agri_component,
            plus_amount_only,
            supplementary_unit,
            nothing,
        ]
    }


@pytest.fixture
def condition_codes() -> Dict[str, MeasureConditionCode]:
    return {
        mcc.code: mcc
        for mcc in [
            factories.MeasureConditionCodeFactory(code="A"),
            factories.MeasureConditionCodeFactory(code="B"),
            factories.MeasureConditionCodeFactory(code="Y"),
        ]
    }


@pytest.fixture
def action_codes() -> Dict[str, MeasureAction]:
    return {
        a.code: a
        for a in [
            factories.MeasureActionFactory(code="01"),
            factories.MeasureActionFactory(code="09"),
            factories.MeasureActionFactory(code="24"),
            factories.MeasureActionFactory(code="299"),
        ]
    }


@pytest.fixture
def certificates():
    d_type = factories.CertificateTypeFactory(sid="D")
    nine_type = factories.CertificateTypeFactory(sid="9")
    return {
        "D017": factories.CertificateFactory(sid="017", certificate_type=d_type),
        "D018": factories.CertificateFactory(sid="018", certificate_type=d_type),
        "9100": factories.CertificateFactory(sid="100", certificate_type=nine_type),
    }


@pytest.fixture
def monetary_units() -> Dict[str, MonetaryUnit]:
    return {
        m.code: m
        for m in [
            factories.MonetaryUnitFactory(code="EUR"),
            factories.MonetaryUnitFactory(code="GBP"),
            factories.MonetaryUnitFactory(code="XEM"),
        ]
    }


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
def measurements(
    measurement_units,
    unit_qualifiers,
) -> Dict[Tuple[str, Optional[str]], Measurement]:
    measurements = [
        *[
            factories.MeasurementFactory(
                measurement_unit=m,
                measurement_unit_qualifier=None,
            )
            for m in measurement_units
        ],
        factories.MeasurementFactory(
            measurement_unit=measurement_units[1],
            measurement_unit_qualifier=unit_qualifiers[0],
        ),
    ]
    return {
        (
            m.measurement_unit.code,
            m.measurement_unit_qualifier.code if m.measurement_unit_qualifier else None,
        ): m
        for m in measurements
    }


@pytest.fixture
def duty_sentence_parser(
    duty_expressions: Dict[int, DutyExpression],
    monetary_units: Dict[str, MonetaryUnit],
    measurements: Dict[Tuple[str, Optional[str]], Measurement],
) -> DutySentenceParser:
    return DutySentenceParser(
        duty_expressions.values(),
        monetary_units.values(),
        measurements.values(),
    )


@pytest.fixture
def condition_duty_sentence_parser(
    duty_expressions: Dict[int, DutyExpression],
    monetary_units: Dict[str, MonetaryUnit],
    measurements: Dict[Tuple[str, Optional[str]], Measurement],
) -> DutySentenceParser:
    return DutySentenceParser(
        duty_expressions.values(),
        monetary_units.values(),
        measurements.values(),
        MeasureConditionComponent,
    )


@pytest.fixture
def get_component_data(duty_expressions, monetary_units, measurements) -> Callable:
    def getter(
        duty_expression_id,
        amount,
        monetary_unit_code,
        measurement_codes,
    ) -> Dict:
        return {
            "duty_expression": duty_expressions.get(duty_expression_id),
            "duty_amount": amount,
            "monetary_unit": monetary_units.get(monetary_unit_code),
            "component_measurement": measurements.get(measurement_codes),
        }

    return getter


@pytest.fixture(
    params=(
        ("4.000%", [(1, 4.0, None, None)]),
        ("1.230 EUR / kg", [(1, 1.23, "EUR", ("KGM", None))]),
        ("0.300 XEM / 100 kg / lactic.", [(1, 0.3, "XEM", ("DTN", "Z"))]),
        (
            "12.900% + 20.000 EUR / kg",
            [(1, 12.9, None, None), (4, 20.0, "EUR", ("KGM", None))],
        ),
        ("kg", [(99, None, None, ("KGM", None))]),
        ("100 kg", [(99, None, None, ("DTN", None))]),
        ("1.000 EUR", [(1, 1.0, "EUR", None)]),
        ("0.000% + AC", [(1, 0.0, None, None), (12, None, None, None)]),
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
def reversible_duty_sentence_data(request, get_component_data):
    """Duty sentence test cases that are syntactically correct and are also
    formatted correctly."""
    expected, component_data = request.param
    return expected, [get_component_data(*args) for args in component_data]


@pytest.fixture(
    params=(
        ("20.0 EUR/100kg", [(1, 20.0, "EUR", ("DTN", None))]),
        ("1.0 EUR/1000 p/st", [(1, 1.0, "EUR", ("MIL", None))]),
    ),
    ids=[
        "parses_without_spaces",
        "parses_without_commas",
    ],
)
def irreversible_duty_sentence_data(request, get_component_data):
    """Duty sentence test cases that are syntactically correct but are not in
    the canonical rendering format with spaces and commas in the correct
    places."""
    expected, component_data = request.param
    return expected, [get_component_data(*args) for args in component_data]


def erga_omnes():
    return factories.GeographicalAreaFactory.create(area_code=1, area_id=1011)


@pytest.fixture
def measure_form(session_with_workbasket, erga_omnes):
    measure = factories.MeasureFactory.create()
    data = model_to_dict(measure)
    start_date = data["valid_between"].lower
    data.update(
        start_date_0=start_date.day,
        start_date_1=start_date.month,
        start_date_2=start_date.year,
    )

    return MeasureForm(
        data=data,
        instance=Measure.objects.with_duty_sentence().first(),
        request=session_with_workbasket,
    )


@pytest.fixture()
def additional_code():
    return factories.AdditionalCodeFactory.create()


@pytest.fixture()
def measure_type():
    return factories.MeasureTypeFactory.create(
        valid_between=TaricDateRange(datetime.date(2020, 1, 1), None, "[)"),
    )


@pytest.fixture()
def regulation():
    return factories.RegulationFactory.create()


@pytest.fixture()
def commodity1():
    return factories.GoodsNomenclatureFactory.create()


@pytest.fixture()
def commodity2():
    return factories.GoodsNomenclatureFactory.create()


@pytest.fixture()
def mock_request(rf, valid_user, valid_user_client):
    request = rf.get("/")
    request.user = valid_user
    request.session = valid_user_client.session
    request.requests_session = requests.Session()
    return request
