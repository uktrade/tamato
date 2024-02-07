from datetime import datetime

from django.core.exceptions import ObjectDoesNotExist
from django.template.loader import render_to_string
from lark import Lark
from lark import Transformer
from lark import UnexpectedInput

from measures import models
from measures.validators import ApplicabilityCode


class DutySyntaxError(SyntaxError):
    def __str__(self):
        context, _, column = self.args
        if self.hint:
            hint_display = f" \n\n{self.hint} "
        else:
            hint_display = ""
        return f"{self.label} at character {column}.{hint_display}\n\n{context}"


class DutyInvalidDutyExpression(DutySyntaxError):
    label = "No matching duty expression found"
    hint = "Check the validity period of the duty expression and that you are using the correct prefix."


class DutyInvalidMonetaryUnit(DutySyntaxError):
    label = "No matching monetary unit or percentage amount found"
    hint = f"Check the validity period of the monetary unit and that you are using the correct code. If the amount is a percentage make sure to include the % symbol after the number."


class DutyInvalidMeasurementUnit(DutySyntaxError):
    label = "No matching measurement unit found"
    hint = "Check the validity period of the measurement unit and that you are using the correct abbreviation (not code)."


class DutyInvalidMeasurementUnitQualififer(DutySyntaxError):
    label = "No matching measurement unit qualifier found"
    hint = "Check the validity period of the measurement unit qualifier and that you are using the correct abbreviation."


class DutySentenceParser:
    """A dumb parser that does minimal validation and only matches a duty
    sentence according to a set pattern."""

    def __init__(self, date=datetime.now()):
        duty_expressions = models.DutyExpression.objects.as_at(date)
        monetary_units = models.MonetaryUnit.objects.as_at(date)
        measurement_units = models.MeasurementUnit.objects.as_at(date)
        measurement_unit_qualifiers = models.MeasurementUnitQualifier.objects.as_at(
            date,
        )

        duty_expression_amount_mandatory = render_to_string(
            "duties/parser/duty_expression.jinja",
            {
                "code": ApplicabilityCode.MANDATORY,
                "duty_expressions": duty_expressions,
            },
        )
        duty_expression_amount_not_permitted = render_to_string(
            "duties/parser/duty_expression.jinja",
            {
                "code": ApplicabilityCode.NOT_PERMITTED,
                "duty_expressions": duty_expressions,
            },
        )
        monetary_unit_rule = render_to_string(
            "duties/parser/unit_code.jinja",
            {"units": monetary_units},
        )
        measurement_unit_rule = render_to_string(
            "duties/parser/unit_abbreviation.jinja",
            {"units": measurement_units},
        )
        measurement_unit_qualifier_rule = render_to_string(
            "duties/parser/unit_abbreviation.jinja",
            {"units": measurement_unit_qualifiers},
        )
        self.parser = Lark(
            f"""
            slash: "/"

            # DutyExpression
            !expr_amount_mandatory: {duty_expression_amount_mandatory}
            !expr_amount_not_permitted: {duty_expression_amount_not_permitted}
            # variables output as "-" | "+" | "MAX" | "MIN" | "NIHIL" | "+ AC" etc. see template

            duty_amount: NUMBER

            # MonetaryUnit
            !monetary_unit: "%" | {monetary_unit_rule}

            # MeasurementUnit
            !measurement_unit: {measurement_unit_rule}

            # MeasurementUnitQualifier
            !measurement_unit_qualifier: {measurement_unit_qualifier_rule}

            # MeasureComponent
            !phrase: expr_amount_not_permitted [slash measurement_unit [measurement_unit_qualifier]]
                | duty_amount monetary_unit [slash measurement_unit [measurement_unit_qualifier]]
                | expr_amount_mandatory duty_amount monetary_unit [slash measurement_unit [measurement_unit_qualifier]]

            !sentence: phrase+

            %import common.NUMBER
            %import common.WS
            %ignore WS

            """,
            start="sentence",
        )

    def parse(self, duty_sentence):
        try:
            return self.parser.parse(duty_sentence)

        except UnexpectedInput as u:
            exc_class = u.match_examples(
                self.parser.parse,
                {
                    DutyInvalidDutyExpression: [
                        "10% + Blah duty (reduced)",
                        "5.5% + ABCDE + Some other fake duty expression",
                        "10%&@#^&",
                        "ABC",
                        "@(*&$#)",
                    ],
                    DutyInvalidMonetaryUnit: [
                        "10% + 100 ABC / 100 kg",
                        "100 DEF",
                        "5.5% + 100 XYZ + AC (reduced)",
                    ],
                    DutyInvalidMeasurementUnit: [
                        "10% + 100 GBP / 100 abc",
                        "100 GBP / foobar measurement",
                        "5.5% + 100 EUR / foobar",
                    ],
                    DutyInvalidMeasurementUnitQualififer: [
                        "10% + 100 GBP / 100 kg ABC",
                        "100 GBP / 100 kg XYZ foo bar",
                        "5.5% + 100 EUR / % vol foo bar",
                    ],
                },
                use_accepts=True,
            )
            if not exc_class:
                raise
            raise exc_class(u.get_context(duty_sentence), u.line, u.column)


# Measure components (only 1):
#         m1: duty.expression.id (01 or 37 if NIHIL)
#         m2: duty.amount
#         m3: monetary.unit.code
#         m4: measurement.unit.code
#         m5: measurement.unit.qualifier.code


class DutyTransformer(Transformer):
    """Takes the output from the DutySentenceParser and returns objects for
    DutyExpressions, MonetaryUnits, MeasurementUnits and
    MeasurementUnitQualifiers then validates that they can be used together."""

    def __init__(self, *args, **kwargs):
        self.date = kwargs.pop("date")
        super().__init__()

    @property
    def duty_expressions(self):
        return (
            models.DutyExpression.objects.as_at(self.date)
            .exclude(prefix__isnull=True)
            .order_by("sid")
        )

    def sentence(self, items):
        return items

    def phrase(self, items):
        cleaned_items = [item for item in items if item is not None]
        return {item[0]: item[1] for item in cleaned_items}

    def expr_amount_mandatory(self, value):
        (value,) = value
        try:
            match = self.duty_expressions.filter(
                prefix__iexact=value,
                duty_amount_applicability_code=ApplicabilityCode.MANDATORY,
            ).first()
        except ObjectDoesNotExist:
            match = None
        return ("duty_expression", match)

    def expr_amount_not_permitted(self, value):
        (value,) = value
        try:
            match = self.duty_expressions.filter(
                prefix__iexact=value,
                duty_amount_applicability_code=ApplicabilityCode.NOT_PERMITTED,
            ).first()
        except ObjectDoesNotExist:
            match = None
        return ("duty_expression", match)

    def duty_amount(self, value):
        (value,) = value
        return ("duty_amount", float(value))

    def monetary_unit(self, value):
        (value,) = value
        if value == "%":
            return None
        try:
            match = models.MonetaryUnit.objects.as_at(self.date).get(code__iexact=value)
        except ObjectDoesNotExist:
            match = None
        return ("monetary_unit", match)

    def measurement_unit(self, value):
        (value,) = value
        try:
            match = models.MeasurementUnit.objects.as_at(self.date).get(
                abbreviation__iexact=value,
            )
        except ObjectDoesNotExist:
            match = None
        return ("measurement_unit", match)

    def measurement_unit_qualifier(self, value):
        (value,) = value
        try:
            match = models.MeasurementUnitQualifier.objects.as_at(self.date).get(
                abbreviation__iexact=value,
            )
        except ObjectDoesNotExist:
            match = None
        return ("measurement_unit_qualifier", match)

    def slash(self, value):
        return None
