from functools import reduce
from typing import List
from typing import Union

from parsec import choice
from parsec import joint
from parsec import optional
from parsec import Parser
from parsec import regex
from parsec import spaces
from parsec import string
from parsec import try_choice

from common.validators import ApplicabilityCode
from measures.models import DutyExpression
from measures.models import MeasureComponent
from measures.models import Measurement
from measures.models import MeasurementUnit
from measures.models import MeasurementUnitQualifier
from measures.models import MonetaryUnit

# Used to represent percentage or currency values.
Amount = float


class DutySentenceParser:
    """
    A duty expression defines what elements are permitted in a measure component
    for each type of duty expression: amount, monetary unit and measurement.
    They also include the prefix that must be matched at the start of the expression.
    E.g. (2, '+', MANDATORY, PERMITTED, PERMITTED) describes things like '+ 1.23 EUR/kg'

    A parsed measure component references a duty expression ID
    and will potentially have values for the amount, monetary unit and measurement.
    """

    def __init__(
        self,
        duty_expressions: List[DutyExpression],
        monetary_units: List[MonetaryUnit],
        permitted_measurements: List[Measurement],
    ):
        empty = string("").result(None)

        def token(s: str) -> Parser:
            """Matches a string surrounded optionally by whitespace."""
            return spaces() >> string(s) << spaces()

        def code(
            obj: Union[
                MonetaryUnit,
            ]
        ) -> Parser:
            """Matches an code and returns the associated object."""
            return string(obj.code).result(obj)

        def abbrev(
            obj: Union[
                MeasurementUnit,
                MeasurementUnitQualifier,
            ]
        ) -> Parser:
            """Matches an abbreviation and returns the associated object.
            Humans cannot be relied upon to use spaces or thousand separators
            correctly so these can ignored."""
            return reduce(
                try_choice,
                [
                    string(obj.abbreviation),
                    string(obj.abbreviation.replace(" ", "")),
                    string(obj.abbreviation.replace("1,000", "1000")),
                    string(obj.abbreviation.replace(" ", "").replace("1,000", "1000")),
                ],
            ).result(obj)

        def if_applicable(
            has_this: ApplicabilityCode, parser: Parser, default: Parser = empty
        ) -> Parser:
            """Matches a value depending on the passed applicability code."""
            if has_this == ApplicabilityCode.PERMITTED:
                return parser ^ default
            elif has_this == ApplicabilityCode.NOT_PERMITTED:
                return empty
            else:
                return parser

        # Decimal numbers are a sequence of digits (without a left-trailing zero)
        # followed optionally by a decimal point and a number of digits (we have seen
        # some percentage values have three decimal digits).  Money values are similar
        # but only 2 digits are allowed after the decimal.
        # TODO: work out if float will cause representation problems.
        decimal = regex(r"(0|[1-9][0-9]*)([.][0-9]+)?").parsecmap(float)

        # Specific duty amounts reference various types of unit.
        # For monetary units, the expression just contains the same code as is
        # present in the sentence. Percentage values correspond to no unit.
        self._monetary_unit = reduce(choice, map(code, monetary_units)) if monetary_units else empty
        percentage_unit = token("%").result(None)

        # For measurement units and qualifiers, we match a human-readable version
        # of the unit to its internal code. Units by themselves are always allowed,
        # but only some combinations of units and qualifiers are permitted.
        def measurement(m: Measurement) -> Parser:
            unit = abbrev(m.measurement_unit)
            qualifier = (
                (token("/") >> abbrev(m.measurement_unit_qualifier))
                if m.measurement_unit_qualifier
                else empty
            )
            return joint(unit, qualifier).result(m)

        # We have to try and parse measurements with qualifiers first
        # else we may match the first part of a unit without the qualifier
        some_qualifier = [
            m
            for m in permitted_measurements
            if m.measurement_unit_qualifier is not None
        ]
        none_qualifier = [
            m for m in permitted_measurements if m.measurement_unit_qualifier is None
        ]
        measurements = list(map(measurement, [*some_qualifier, *none_qualifier]))
        self._measurement = reduce(try_choice, measurements) if measurements else empty

        # Each measure component can have an amount, monetary unit and measurement.
        # Which expression elements are allowed in a component is controlled by
        # the duty epxression applicability codes. We convert the duty expressions
        # into parsers that will only parse the elements that are permitted for this type.
        def component(duty_exp: DutyExpression) -> Parser:
            """Matches a string prefix and returns the associated type id,
            along with any parsed amounts and units according to their applicability,
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
                has_measurement, optional(token("/")) >> self._measurement
            )

            component = joint(id, this_value, this_monetary_unit, this_measurement)
            measurement_only = joint(id, this_measurement).parsecmap(
                lambda t: (t[0], None, None, t[1])
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
                lambda exp: MeasureComponent(
                    duty_expression=exp[0],
                    duty_amount=exp[1],
                    monetary_unit=exp[2],
                    component_measurement=exp[3],
                )
            )

        # Duty sentences can only be of a finite length – each expression may only
        # appear once and in order of increasing expression id. So we try all expressions
        # in order and filter out the None results for ones that did not match.
        expressions = [
            component(exp) ^ empty
            for exp in sorted(duty_expressions, key=lambda e: e.sid)
        ]
        self._sentence = joint(*expressions).parsecmap(
            lambda sentence: [exp for exp in sentence if exp is not None]
        )

    @property
    def monetary_unit_parser(self) -> Parser:
        """A parser that can parse monetary units."""
        return self._monetary_unit

    @property
    def measurement_parser(self) -> Parser:
        """A parser that can parse measurements, including lone units
        and units paired with permitted qualifiers."""
        return self._measurement

    @property
    def sentence_parser(self) -> Parser:
        """A parser that can parse a single duty sentence."""
        return self._sentence

    def parse(self, s: str) -> List[MeasureComponent]:
        """Parses an entire string as a duty sentence, returning
        a list of the parsed measure components. Throws an error
        if the string cannot be successfully parsed."""
        return self.sentence_parser.parse_strict(s)
