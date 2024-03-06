from datetime import datetime
from typing import Sequence

from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError
from django.db.models.expressions import RawSQL
from lark import Lark
from lark import Transformer
from lark import UnexpectedInput

from measures import models
from measures.validators import ApplicabilityCode


class DutySyntaxError(SyntaxError):
    def __str__(self):
        context, _, column = self.args
        hint_display = f" \n\n{self.hint} "
        return f"{self.label} at character {column}.{hint_display}"


class DutyAmountRequired(DutySyntaxError):
    label = "A duty amount is required"
    hint = "Check the duty amount applicability code of the duty expression and that you have included a monetary unit or percentage."


class InvalidDutyExpression(DutySyntaxError):
    label = "No matching duty expression found"
    hint = "Check the validity period of the duty expression and that you are using the correct prefix."


class InvalidMonetaryUnit(DutySyntaxError):
    label = "No matching monetary unit or percentage amount found"
    hint = f"Check the validity period of the monetary unit and that you are using the correct code. If the amount is a percentage make sure to include the % symbol after the number."


class InvalidMeasurementUnit(DutySyntaxError):
    label = "No matching measurement unit found"
    hint = "Check the validity period of the measurement unit and that you are using the correct abbreviation (not code)."


class InvalidMeasurementUnitQualififer(DutySyntaxError):
    label = "No matching measurement unit qualifier found"
    hint = "Check the validity period of the measurement unit qualifier and that you are using the correct abbreviation."


INVALID_DUTY_EXPERESSION_MESSAGE = (
    f"{InvalidDutyExpression.label}. {InvalidDutyExpression.hint}"
)
INVALID_DUTY_MONETARY_UNIT_MESSAGE = (
    f"{InvalidMonetaryUnit.label}. {InvalidMonetaryUnit.hint}"
)
INVALID_DUTY_MEASUREMENT_UNIT_MESSAGE = (
    f"{InvalidMeasurementUnit.label}. {InvalidMeasurementUnit.hint}"
)
INVALID_DUTY_MEASUREMENT_UNIT_QUALIFIER_MESSAGE = (
    f"{InvalidMeasurementUnitQualififer.label}. {InvalidMeasurementUnitQualififer.hint}"
)


class DutySentenceParser:
    """A dumb parser that does minimal validation and only matches a duty
    sentence according to a set pattern."""

    @staticmethod
    def create_rule(items, field_name, strip=False):
        output = []
        for item in items:
            if getattr(item, field_name):
                val = getattr(item, field_name)
                if strip:
                    # For measurement abbreviations we want to be able to match with and without spaces and commas (in the case of measurement units in the thousands) so add the spaceless and commaless values to the rule as well
                    unique_values = set(
                        [
                            val,
                            val.replace(" ", ""),
                            val.replace(",", ""),
                            val.replace(",", "").replace(" ", ""),
                        ],
                    )
                    for value in unique_values:
                        output.append(f'"{value}"i | ')
                else:
                    output.append(f'"{val}"i | ')
        # cut off final " | "
        return "".join(output)[0:-3]

    def __init__(
        self,
        date: datetime = datetime.now(),
        duty_expressions: Sequence[models.DutyExpression] = None,
        monetary_units: Sequence[models.MonetaryUnit] = None,
        measurements: Sequence[models.Measurement] = None,
        measurement_units: Sequence[models.MeasurementUnit] = None,
        measurement_unit_qualifiers: Sequence[models.MeasurementUnitQualifier] = None,
    ):
        """
        This class can be optionally loaded up with custom lists of duty
        expressions, monetary units, and measurements on init.

        Mainly useful for testing.
        """
        duty_expressions = models.DutyExpression.objects.as_at(date) or duty_expressions
        monetary_units = models.MonetaryUnit.objects.as_at(date) or monetary_units
        measurement_units = (
            models.MeasurementUnit.objects.as_at(date) or measurement_units
        )
        measurement_unit_qualifiers = (
            models.MeasurementUnitQualifier.objects.as_at(date)
            or measurement_unit_qualifiers
        )
        measurements = models.Measurement.objects.as_at(date) or measurements

        amount_mandatory = duty_expressions.filter(
            duty_amount_applicability_code=ApplicabilityCode.MANDATORY,
        )
        amount_permitted = duty_expressions.filter(
            duty_amount_applicability_code=ApplicabilityCode.PERMITTED,
        )
        amount_not_permitted = duty_expressions.filter(
            duty_amount_applicability_code=ApplicabilityCode.NOT_PERMITTED,
        )

        self.parser_rules = f"""
            slash: "/"

            # DutyExpression
            !expr_amount_mandatory: {self.create_rule(amount_mandatory, "prefix")}
            !expr_amount_permitted: {self.create_rule(amount_permitted, "prefix")}
            !expr_amount_not_permitted: {self.create_rule(amount_not_permitted, "prefix")}
            # variables output as "-" | "+" | "MAX" | "MIN" | "NIHIL" | "+ AC" etc

            duty_amount: NUMBER

            # MonetaryUnit
            !monetary_unit: "%" | {self.create_rule(monetary_units, "code")}

            # MeasurementUnit
            !measurement_unit: {self.create_rule(measurement_units, "abbreviation", strip=True)}

            # MeasurementUnitQualifier
            !measurement_unit_qualifier: {self.create_rule(measurement_unit_qualifiers, "abbreviation", strip=True)}

            # MeasureComponent
            !phrase: expr_amount_not_permitted [slash measurement_unit [slash measurement_unit_qualifier]]
                | duty_amount monetary_unit [slash measurement_unit [slash measurement_unit_qualifier]]
                | (expr_amount_mandatory | expr_amount_permitted) duty_amount monetary_unit [slash measurement_unit [slash measurement_unit_qualifier]]
                | measurement_unit [slash measurement_unit_qualifier]

            !sentence: phrase+

            %import common.NUMBER
            %import common.WS
            %ignore WS

            """

        self.parser = Lark(
            self.parser_rules,
            start="sentence",
        )

        self.transformer = DutyTransformer(
            date=datetime.now(),
            duty_expressions=duty_expressions,
            monetary_units=monetary_units,
            measurements=measurements,
            measurement_units=measurement_units,
            measurement_unit_qualifiers=measurement_unit_qualifiers,
        )

    def parse(self, duty_sentence):
        try:
            return self.parser.parse(duty_sentence)

        except UnexpectedInput as u:
            exc_class = u.match_examples(
                self.parser.parse,
                {
                    InvalidDutyExpression: [
                        "10% + Blah duty (reduced)",
                        "5.5% + ABCDE + Some other fake duty expression",
                        "10%&@#^&",
                        "ABC",
                        "@(*&$#)",
                    ],
                    DutyAmountRequired: [
                        "+",
                    ],
                    InvalidMonetaryUnit: [
                        "10% + 100 ABC / 100 kg",
                        "100 DEF",
                        "5.5% + 100 XYZ + AC (reduced)",
                    ],
                    InvalidMeasurementUnit: [
                        "10% + 100 GBP / 100 abc",
                        "100 GBP / foobar measurement",
                        "5.5% + 100 EUR / foobar",
                    ],
                    InvalidMeasurementUnitQualififer: [
                        "10% + 100 GBP / 100 kg / ABC",
                        "100 GBP / 100 kg / XYZ foo bar",
                        "5.5% + 100 EUR / % vol / foo bar",
                    ],
                },
                use_accepts=True,
            )
            if not exc_class:
                raise
            raise exc_class(u.get_context(duty_sentence), u.line, u.column)

    def transform(self, duty_sentence):
        tree = self.parse(duty_sentence)
        return self.transformer.transform(tree)


class DutyTransformer(Transformer):
    """Takes the output from the DutySentenceParser and returns objects for
    DutyExpressions, MonetaryUnits, MeasurementUnits and
    MeasurementUnitQualifiers then validates that they can be used together."""

    def __init__(self, *args, **kwargs):
        self.date = kwargs.pop("date")
        self.duty_expressions = kwargs.pop("duty_expressions")
        self.measurements = kwargs.pop("measurements")
        self.monetary_units = kwargs.pop("monetary_units")
        self.measurement_units = kwargs.pop("measurement_units")
        self.measurement_unit_qualifiers = kwargs.pop("measurement_unit_qualifiers")
        super().__init__()

    def validate_duty_expressions(self, transformed):
        duty_expressions = (
            models.DutyExpression.objects.as_at(self.date)
            .exclude(prefix__isnull=True)
            .order_by("sid")
        )

        duty_expression_sids = [d.sid for d in duty_expressions]
        supplementary_unit = models.DutyExpression.objects.as_at(self.date).get(sid=99)

        if len(transformed) == 1:
            phrase = transformed[0]
            duty_expression = phrase.get("duty_expression", "")
            if (
                duty_expression == ""
                and "duty_amount" not in transformed[0].keys()
                and "measurement_unit" in transformed[0].keys()
            ):
                phrase["duty_expression"] = supplementary_unit
                return

        for phrase in transformed:
            duty_expression = phrase.get("duty_expression", "")
            match = (
                models.DutyExpression.objects.as_at(self.date)
                .filter(
                    prefix__iexact=duty_expression,
                    sid__in=duty_expression_sids,
                )
                .order_by("sid")
                .first()
            )
            if match is None:
                potential_match = (
                    models.DutyExpression.objects.as_at(self.date)
                    .filter(
                        prefix__iexact=duty_expression,
                    )
                    .order_by("sid")
                    .first()
                )
                raise ValidationError(
                    f"A duty expression cannot be used more than once in a duty sentence. Matching expression: {potential_match.description} ({potential_match.prefix})",
                )

            # Each duty expression can only be used once in a sentence and in order of increasing
            # SID so once we have a match, remove it from the list of duty expression sids
            duty_expression_sids.remove(match.sid)
            # Update with the matching DutyExpression we found
            phrase["duty_expression"] = match

        transformed_duty_expression_sids = [
            phrase["duty_expression"].sid for phrase in transformed
        ]

        if transformed_duty_expression_sids != sorted(transformed_duty_expression_sids):
            raise ValidationError(
                "Duty expressions must be used in the duty sentence in ascending order of SID.",
            )

    @staticmethod
    def validate_according_to_applicability_code(
        code,
        duty_expression,
        item,
        item_name,
    ):
        if code == ApplicabilityCode.MANDATORY and item is None:
            raise ValidationError(
                f"Duty expression {duty_expression.description} ({duty_expression.prefix}) requires a {item_name}.",
            )
        if code == ApplicabilityCode.NOT_PERMITTED and item:
            if isinstance(item, object):
                message = f"{item_name.capitalize()} {item.abbreviation} ({item.code}) cannot be used with duty expression {duty_expression.description} ({duty_expression.prefix})."
            else:
                message = f"{item_name.capitalize()} cannot be used with duty expression {duty_expression.description} ({duty_expression.prefix})."
            raise ValidationError(message)

    def validate_measurement(self, unit, qualifier):
        try:
            self.measurements.get(
                measurement_unit=unit,
                measurement_unit_qualifier=qualifier,
            )
        except ObjectDoesNotExist:
            raise ValidationError(
                f"Measurement unit qualifier {qualifier.abbreviation} cannot be used with measurement unit {unit.abbreviation}.",
            )

    def validate_phrase(self, phrase):
        # Each measure component can have an amount, monetary unit and measurement.
        # Which expression elements are allowed in a component is controlled by
        # the duty expression applicability codes
        duty_expression = phrase["duty_expression"]
        amount_code = duty_expression.duty_amount_applicability_code
        monetary_code = duty_expression.monetary_unit_applicability_code
        measurement_unit_code = duty_expression.measurement_unit_applicability_code

        duty_amount = phrase.get("duty_amount", None)
        monetary_unit = phrase.get("monetary_unit", None)
        measurement_unit = phrase.get("measurement_unit", None)
        measurement_unit_qualifier = phrase.get("measurement_unit_qualifier", None)

        self.validate_according_to_applicability_code(
            amount_code,
            duty_expression,
            duty_amount,
            "duty amount",
        )
        self.validate_according_to_applicability_code(
            monetary_code,
            duty_expression,
            monetary_unit,
            "monetary unit",
        )
        self.validate_according_to_applicability_code(
            measurement_unit_code,
            duty_expression,
            measurement_unit,
            "measurement unit",
        )

        # If there is a measurement unit qualifier, validate that it can be used with the measurement
        if measurement_unit and measurement_unit_qualifier:
            self.validate_measurement(
                measurement_unit,
                measurement_unit_qualifier,
            )

    def validate_sentence(self, transformed):
        for phrase in transformed:
            self.validate_phrase(phrase)

    def is_valid(self, transformed):
        self.validate_duty_expressions(transformed)
        self.validate_sentence(transformed)

        return True

    def transform(self, tree):
        # perform validation and raise any errors before returning the transformed tree
        transformed = self._transform_tree(tree)
        if self.is_valid(transformed):
            return transformed

    def sentence(self, items):
        return items

    def phrase(self, items):
        cleaned_items = [item for item in items if item is not None]
        return {item[0]: item[1] for item in cleaned_items}

    def expr_amount_mandatory(self, value):
        (value,) = value
        return ("duty_expression", value)

    def expr_amount_not_permitted(self, value):
        (value,) = value
        return ("duty_expression", value)

    def expr_amount_permitted(self, value):
        (value,) = value
        return ("duty_expression", value)

    def duty_amount(self, value):
        (value,) = value
        return ("duty_amount", float(value))

    def monetary_unit(self, value):
        (value,) = value
        if value == "%":
            return None
        match = models.MonetaryUnit.objects.as_at(self.date).get(code__iexact=value)
        return ("monetary_unit", match)

    def measurement_unit(self, value):
        (value,) = value
        annotated_measurement_units = models.MeasurementUnit.objects.as_at(
            self.date,
        ).annotate(
            abbreviation_stripped=RawSQL(
                "REPLACE(REPLACE(abbreviation, %s, ''), %s, '')",
                (" ", ","),
            ),
        )
        match = annotated_measurement_units.get(
            abbreviation_stripped__iexact=value.replace(" ", "").replace(",", ""),
        )
        return ("measurement_unit", match)

    def measurement_unit_qualifier(self, value):
        (value,) = value
        annotated_measurement_unit_qualifiers = (
            self.measurement_unit_qualifiers.annotate(
                abbreviation_stripped=RawSQL(
                    "REPLACE(REPLACE(abbreviation, %s, ''), %s, '')",
                    (" ", ","),
                ),
            )
        )
        match = annotated_measurement_unit_qualifiers.get(
            abbreviation_stripped__iexact=value.replace(" ", "").replace(",", ""),
        )
        return ("measurement_unit_qualifier", match)

    def slash(self, value):
        return None
