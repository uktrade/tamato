from __future__ import annotations

import re
from datetime import date
from datetime import datetime
from decimal import Decimal
from functools import reduce
from itertools import chain
from typing import Dict
from typing import Iterable
from typing import Iterator
from typing import Match
from typing import Optional
from typing import Tuple
from typing import Union

from parsec import Parser
from parsec import Value
from parsec import joint
from parsec import optional
from parsec import regex
from parsec import spaces
from parsec import string
from parsec import try_choice

from certificates.models import Certificate
from common.models.trackedmodel import TrackedModel
from common.validators import ApplicabilityCode
from measures.models import DutyExpression
from measures.models import MeasureAction
from measures.models import MeasureComponent
from measures.models import MeasureCondition
from measures.models import MeasureConditionCode
from measures.models import MeasureConditionComponent
from measures.models import Measurement
from measures.models import MeasurementUnit
from measures.models import MeasurementUnitQualifier
from measures.models import MonetaryUnit
from measures.util import convert_eur_to_gbp

# Used to represent percentage or currency values.
Amount = Decimal


# A parser that successfully matches nothing
empty: Parser = string("").result(None)


def token(s: str) -> Parser:
    """Matches a string surrounded optionally by whitespace."""
    return spaces() >> string(s) << spaces()


def code(obj: MonetaryUnit) -> Parser:
    """Matches a code and returns the associated object."""
    return string(obj.code).result(obj)


def abbrev(
    obj: Union[
        MeasurementUnit,
        MeasurementUnitQualifier,
    ],
) -> Parser:
    """
    Matches an abbreviation and returns the associated object.

    Humans cannot be relied upon to use spaces or thousand separators correctly
    so these can ignored.
    """
    return reduce(
        try_choice,
        [
            string(obj.abbreviation),
            string(obj.abbreviation.replace(" ", "")),
            string(obj.abbreviation.replace("1,000", "1000")),
            string(obj.abbreviation.replace(" ", "").replace("1,000", "1000")),
        ],
    ).result(obj)


def measurement(m: Measurement) -> Parser:
    """
    For measurement units and qualifiers, we match a human-readable version of
    the unit to its internal code.

    Units by themselves are always allowed, but only some combinations of units
    and qualifiers are permitted.
    """
    unit = abbrev(m.measurement_unit)
    if m.measurement_unit_qualifier:
        qualifier = token("/") >> abbrev(m.measurement_unit_qualifier)
    else:
        qualifier = empty
    return joint(unit, qualifier).result(m)


def if_applicable(
    has_this: ApplicabilityCode,
    parser: Parser,
    default: Parser = empty,
) -> Parser:
    """Matches a value depending on the passed applicability code."""
    if has_this == ApplicabilityCode.PERMITTED:
        return parser ^ default
    elif has_this == ApplicabilityCode.NOT_PERMITTED:
        return empty
    else:
        return parser


@Parser
def fail(text, index):
    """A parser that always fails if reached."""
    return Value.failure(index, f"'{text}' to match something")


class DutySentenceParser:
    """
    A duty expression defines what elements are permitted in a measure component
    or measure condition component for each type of duty expression: amount,
    monetary unit and measurement. They also include the prefix that must be
    matched at the start of the expression. E.g. (2, '+', MANDATORY, PERMITTED,
    PERMITTED) describes things like '+ 1.23 EUR/kg'.

    A parsed component references a duty expression ID and will potentially have
    values for the amount, monetary unit and measurement.
    """

    def __init__(
        self,
        duty_expressions: Iterable[DutyExpression],
        monetary_units: Iterable[MonetaryUnit],
        permitted_measurements: Iterable[Measurement],
        component_output: Optional[TrackedModel] = MeasureComponent,
    ):
        # Decimal numbers are a sequence of digits (without a left-trailing zero)
        # followed optionally by a decimal point and a number of digits (we have seen
        # some percentage values have three decimal digits).  Money values are similar
        # but only 2 digits are allowed after the decimal.
        # TODO: work out if float will cause representation problems.
        decimal = regex(r"(0|[1-9][0-9]*)([.][0-9]+)?").parsecmap(float)

        # Specific duty amounts reference various types of unit.
        # For monetary units, the expression just contains the same code as is
        # present in the sentence. Percentage values correspond to no unit.
        self._monetary_unit = (
            reduce(try_choice, map(code, monetary_units)) if monetary_units else fail
        )
        percentage_unit = token("%").result(None)

        # We have to try and parse measurements with qualifiers first
        # else we may match the first part of a unit without the qualifier
        with_qualifier = [
            m
            for m in permitted_measurements
            if m.measurement_unit_qualifier is not None
        ]
        no_qualifier = [
            m for m in permitted_measurements if m.measurement_unit_qualifier is None
        ]
        measurements = [measurement(m) for m in chain(with_qualifier, no_qualifier)]
        self._measurement = reduce(try_choice, measurements) if measurements else fail

        # Each measure component can have an amount, monetary unit and measurement.
        # Which expression elements are allowed in a component is controlled by
        # the duty epxression applicability codes. We convert the duty expressions
        # into parsers that will only parse the elements that are permitted for this type.
        def component(duty_exp: DutyExpression) -> Parser:
            """Matches a string prefix and returns the associated type id, along
            with any parsed amounts and units according to their applicability,
            as a 4-tuple of (id, amount, monetary unit, measurement)."""
            prefix = duty_exp.prefix
            has_amount = duty_exp.duty_amount_applicability_code
            has_measurement = duty_exp.measurement_unit_applicability_code
            has_monetary = duty_exp.monetary_unit_applicability_code

            id = token(prefix).result(duty_exp)
            this_value = if_applicable(has_amount, decimal)
            this_monetary_unit = if_applicable(
                has_monetary,
                spaces() >> self._monetary_unit,
                # We must match the percentage if the amount should be there
                # and no monetary unit matches.
                default=(
                    percentage_unit
                    if has_amount == ApplicabilityCode.MANDATORY
                    else optional(percentage_unit)
                ),
            )
            this_measurement = if_applicable(
                has_measurement,
                optional(token("/")) >> self._measurement,
            )

            component = joint(id, this_value, this_monetary_unit, this_measurement)
            measurement_only = joint(id, this_measurement).parsecmap(
                lambda t: (t[0], None, None, t[1]),
            )

            # It's possible for units that contain numbers (e.g. DTN => '100 kg')
            # to be confused with a simple specific duty (e.g 100.0 + kg)
            # So in the case that amounts are only optional and measurements are present,
            # we have to check for just measurements first.
            return (
                measurement_only ^ component
                if has_amount == ApplicabilityCode.PERMITTED
                and has_measurement != ApplicabilityCode.NOT_PERMITTED
                else component
            ).parsecmap(
                lambda exp: component_output(
                    duty_expression=exp[0],
                    duty_amount=exp[1],
                    monetary_unit=exp[2],
                    component_measurement=exp[3],
                ),
            )

        # Duty sentences can only be of a finite length – each expression may only
        # appear once and in order of increasing expression id. So we try all expressions
        # in order and filter out the None results for ones that did not match.
        expressions = (
            [
                component(exp) ^ empty
                for exp in sorted(duty_expressions, key=lambda e: e.sid)
            ]
            if duty_expressions
            else [fail]
        )
        self._sentence = joint(*expressions).parsecmap(
            lambda sentence: [exp for exp in sentence if exp is not None],
        )

    @property
    def monetary_unit_parser(self) -> Parser:
        """A parser that can parse monetary units."""
        return self._monetary_unit

    @property
    def measurement_parser(self) -> Parser:
        """A parser that can parse measurements, including lone units and units
        paired with permitted qualifiers."""
        return self._measurement

    @property
    def sentence_parser(self) -> Parser:
        """A parser that can parse a single duty sentence."""
        return self._sentence

    def parse(self, s: str) -> Iterable[MeasureComponent]:
        """
        Parses an entire string as a duty sentence, returning a list of the
        parsed measure components.

        Throws an error if the string cannot be successfully parsed.
        """
        return self.sentence_parser.parse_strict(s)

    @classmethod
    def get(
        cls,
        forward_time: date,
        component_output: Optional[TrackedModel] = MeasureComponent,
    ) -> DutySentenceParser:
        """Return a DutySentenceParser loaded with expressions and measurements
        that are valid on the passed date."""
        duty_expressions = (
            DutyExpression.objects.as_at(forward_time)
            # Exclude anything which will match all strings
            .exclude(prefix__isnull=True).order_by("sid")
        )
        monetary_units = MonetaryUnit.objects.as_at(forward_time)
        permitted_measurements = (
            Measurement.objects.as_at(forward_time)
            .exclude(measurement_unit__abbreviation__exact="")
            .exclude(
                measurement_unit_qualifier__abbreviation__exact="",
            )
        )

        return DutySentenceParser(
            duty_expressions,
            monetary_units,
            permitted_measurements,
            component_output=component_output,
        )


class SeasonalRateParser:
    """A seasonal rate defines a simple ad valorem duty sentence along with a
    day and month range for which the seasonal rate should be applied."""

    SEASONAL_RATE = re.compile(r"([\d\.]+%) *\((\d\d [A-Z]{3}) *- *(\d\d [A-Z]{3})\)")

    def detect_seasons(self, duty_exp: str) -> Iterable:
        if SeasonalRateParser.SEASONAL_RATE.search(duty_exp):
            for match in SeasonalRateParser.SEASONAL_RATE.finditer(duty_exp):
                rate, start, end = match.groups()
                validity_start = datetime.strptime(start, r"%d %b").date()
                validity_end = datetime.strptime(end, r"%d %b").date()
                yield (
                    rate,
                    validity_start.day,
                    validity_start.month,
                    validity_end.day,
                    validity_end.month,
                )


class ConditionSentenceParser:
    """
    A condition sentence is a string representation of a set of MeasureCondition
    objects.

    The string is formed from a number of conditon phrases that contain a
    condition type, an optional certificate and then an action code. It can also
    contain an optional duty amount which is similar to a duty sentence but only
    accepts a single component and raw codes, no abbreviations.

    - Measure conditions
        c1: condition.code
        c2: requires certificate?
        c3: certificate.type.code
        c4: certificate.code
        c5: action.code (always 01 - apply the amount of the action)

    - Measure components (only 1):
        m1: duty.expression.id (01 or 37 if NIHIL)
        m2: duty.amount
        m3: monetary.unit.code
        m4: measurement.unit.code
        m5: measurement.unit.qualifier.code

    Examples:
    - Cond:  "A cert: D-008 (01):0.000 EUR TNE I ; A (01):172.200 EUR TNE I"
        c1: A      m1: 01
        c2: True   m2: 0.000
        c3: D      m3: EUR
        c4: 008    m4: TNE
        c5: 01     m5: I

        c1: A      m1: 01
        c2: False  m2: 172.200
        c3: N/A    m3: EUR
        c4: N/A    m4: TNE
        c5: 01     m5: I

    - Cond:  "A cert: D-017 (01):0.000 % ; A cert: D-018 (01):28.200 % ; A (01):28.200 %"
        c1: A      m1: 01
        c2: True   m2: 0.000
        c3: D      m3: N/A
        c4: 017    m4: N/A
        c5: 01     m5: N/A

        c1: A      m1: 01
        c2: True   m2: 28.200
        c3: D      m3: N/A
        c4: 018    m4: N/A
        c5: 01     m5: N/A

        c1: A      m1: 01
        c2: False  m2: 28.200
        c3: N/A    m3: N/A
        c4: N/A    m4: N/A
        c5: 01     m5: N/A
    """

    DUTY_PHRASE_REGEX = (
        r"(?:(?P<m1>NIHIL)(?:$)|(?P<m2>\S+)(?:\s|$))"
        r"(?:(?P<m3>\S+)(?:\s|$))?(?:(?P<m4>\S+)(?:\s|$))?"
        r"(?:(?P<m5>\S+)(?:\s|$))?"
    )

    DUTY_PHRASE_PATTERN = re.compile(
        f"^{DUTY_PHRASE_REGEX}",
    )

    CONDITION_PHRASE_PATTERN = re.compile(
        r"^(?P<c1>[A-Z]) (?:(?P<c2>cert:) (?P<c3>[A-Z9])-?(?P<c4>\d{3}) )?\((?P<c5>\d{2,3})\):\s*"
        f"(?:{DUTY_PHRASE_REGEX})?",
    )

    def __init__(
        self,
        duty_expressions: Iterable[DutyExpression],
        monetary_units: Iterable[MonetaryUnit],
        permitted_measurements: Iterable[Measurement],
        condition_codes: Iterable[MeasureConditionCode],
        action_codes: Iterable[MeasureAction],
        eur_gbp_conversion_rate: Optional[float] = None,
    ):
        self.duty_expressions = {int(d.sid): d for d in duty_expressions}
        self.monetary_units: Dict[str, Optional[MonetaryUnit]] = {
            str(m.code): m for m in monetary_units
        }
        self.monetary_units["%"] = None
        self.permitted_measurements = {
            (
                m.measurement_unit.code,
                m.measurement_unit_qualifier.code
                if m.measurement_unit_qualifier
                else None,
            ): m
            for m in permitted_measurements
        }
        self.condition_codes = {str(c.code): c for c in condition_codes}
        self.action_codes = {str(a.code): a for a in action_codes}
        self.certificates: Dict[str, Certificate] = {}
        self.eur_gbp_conversion_rate = eur_gbp_conversion_rate

    def create_component(
        self,
        match: Match[str],
    ) -> Optional[MeasureConditionComponent]:
        if not (match.group("m1") or match.group("m2") or match.group("m3")):
            return None

        return MeasureConditionComponent(
            duty_expression=(
                self.duty_expressions[37]
                if match.group("m1") == "NIHIL"
                else self.duty_expressions[1]
            ),
            duty_amount=(
                Decimal(
                    convert_eur_to_gbp(match.group("m2"), self.eur_gbp_conversion_rate),
                )
                if match.group("m3") == "EUR" and self.eur_gbp_conversion_rate
                else (Decimal(match.group("m2")) if match.group("m2") else None)
            ),
            monetary_unit=(
                self.monetary_units["GBP"]
                if match.group("m3") == "EUR" and self.eur_gbp_conversion_rate
                else (
                    self.monetary_units[match.group("m3")]
                    if match.group("m3")
                    else None
                )
            ),
            component_measurement=self.permitted_measurements[
                (
                    match.group("m4"),
                    match.group("m5"),
                )
            ]
            if (match.group("m4") or match.group("m5"))
            else None,
        )

    def get_certificate(self, match: Match[str]) -> Optional[Certificate]:
        if not match.group("c2") == "cert:":
            return None

        cert_id = match.group("c3") + match.group("c4")
        if cert_id not in self.certificates:
            self.certificates[cert_id] = Certificate.objects.latest_approved().get(
                certificate_type__sid=match.group("c3"),
                sid=match.group("c4"),
            )

        return self.certificates[cert_id]

    def parse(
        self,
        value: str,
    ) -> Iterator[
        Tuple[Optional[MeasureCondition], Optional[MeasureConditionComponent]]
    ]:
        if value.startswith("Cond:"):
            for entry in value.lstrip("Cond:").strip().split(";"):
                match = re.match(self.CONDITION_PHRASE_PATTERN, entry.strip())
                if match:
                    condition = MeasureCondition(
                        condition_code=self.condition_codes[match.group("c1")],
                        required_certificate=self.get_certificate(match),
                        action=self.action_codes[match.group("c5")],
                    )
                    yield (condition, self.create_component(match))
                else:
                    raise ValueError(f"Could not parse condition expression: '{value}'")
        else:
            match = re.match(self.DUTY_PHRASE_PATTERN, value.strip())
            if match:
                yield (None, self.create_component(match))
            else:
                raise ValueError(f"Could not parse condition expression: '{value}'")

    @classmethod
    def get(cls, forward_time: date):
        duty_expressions = (
            DutyExpression.objects.as_at(forward_time)
            # Exclude anything which will match all strings
            .exclude(prefix__isnull=True).order_by("sid")
        )
        monetary_units = MonetaryUnit.objects.as_at(forward_time)
        permitted_measurements = (
            Measurement.objects.as_at(forward_time)
            .exclude(measurement_unit__abbreviation__exact="")
            .exclude(
                measurement_unit_qualifier__abbreviation__exact="",
            )
        )
        condition_codes = MeasureConditionCode.objects.as_at(forward_time)
        action_codes = MeasureAction.objects.as_at(forward_time)
        return ConditionSentenceParser(
            duty_expressions,
            monetary_units,
            permitted_measurements,
            condition_codes,
            action_codes,
        )
