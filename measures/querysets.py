from typing import Union

from django.contrib.postgres.aggregates import StringAgg
from django.db.models import Value, Case, CharField, When, F, Func, Q
from django.db.models.aggregates import Max
from django.db.models.fields import DateField
from django.db.models.functions import Coalesce
from django.db.models.functions import Concat
from django.db.models.functions.comparison import Cast
from django.db.models.functions.comparison import NullIf
from django.db.models.functions.text import Trim
from django_cte.cte import With

import measures
from common.fields import TaricDateRangeField
from common.models.tracked_qs import TrackedModelQuerySet
from common.querysets import ValidityQuerySet
from common.util import EndDate
from common.util import StartDate


class ComponentQuerySet(TrackedModelQuerySet):
    """QuerySet that can be used with MeasureComponent or
    MeasureConditionComponent."""

    def duty_sentence(
        self, component_parent: Union["measures.Measure", "measures.MeasureCondition"]
    ):
        """
        Generate a duty sentence for a given component parent.

        This function calculates and formats a duty sentence for a component parent, which can be either a 'measures.Measure' or a 'measures.MeasureCondition'.

        Args:
            component_parent (Union["measures.Measure", "measures.MeasureCondition"]): The component parent for which to generate the duty sentence.

        Returns:
            str: The formatted duty sentence as a string. If no duty sentence can be generated, an empty string is returned.

        Note:
            The duty sentence is constructed by concatenating various components, including the duty amount, monetary unit code, measurement unit abbreviation, and measurement unit qualifier abbreviation, in a specific format based on their availability and conditions.

        """
        prefix_expression = F("duty_expression__prefix")
        duty_amount_expression = F("duty_amount")
        monetary_unit_code_expression = F("monetary_unit__code")
        measurement_unit_abbreviation_expression = F(
            "component_measurement__measurement_unit__abbreviation"
        )
        measurement_unit_qualifier_abbreviation_expression = F(
            "component_measurement__measurement_unit_qualifier__abbreviation"
        )

        def concatenate_expression(
            duty_amount,
            monetary_unit_code,
            measurement_unit_abbreviation,
            measurement_unit_qualifier_abbreviation,
        ):
            return Concat(
                Case(
                    When(
                        Q(duty_expression__prefix__isnull=True)
                        | Q(duty_expression__prefix=""),
                        then=Value(""),
                    ),
                    default=Concat(prefix_expression, Value(" ")),
                ),
                duty_amount,
                Case(
                    When(
                        monetary_unit=None, duty_amount__isnull=False, then=Value("%")
                    ),
                    When(duty_amount__isnull=True, then=Value("")),
                    default=Concat(Value(" "), monetary_unit_code),
                ),
                Case(
                    When(
                        Q(component_measurement=None)
                        | Q(component_measurement__measurement_unit=None)
                        | Q(component_measurement__measurement_unit__abbreviation=None),
                        then=Value(""),
                    ),
                    When(
                        monetary_unit__isnull=True, then=measurement_unit_abbreviation
                    ),
                    default=Concat(Value(" / "), measurement_unit_abbreviation),
                ),
                Case(
                    When(
                        component_measurement__measurement_unit_qualifier__abbreviation=None,
                        then=Value(""),
                    ),
                    default=Concat(
                        Value(" / "), measurement_unit_qualifier_abbreviation
                    ),
                ),
                output_field=CharField(),
            )

        component_qs = component_parent.components.approved_up_to_transaction(
            component_parent.transaction,
        )
        if not component_qs:
            return ""

        latest_transaction_id = component_qs.aggregate(
            latest_transaction_id=Max("transaction_id"),
        ).get("latest_transaction_id")
        component_qs = component_qs.filter(transaction_id=latest_transaction_id)

        duty_sentence = component_qs.aggregate(
            duty_sentence=StringAgg(
                expression=Trim(
                    concatenate_expression(
                        duty_amount_expression,
                        monetary_unit_code_expression,
                        measurement_unit_abbreviation_expression,
                        measurement_unit_qualifier_abbreviation_expression,
                    ),
                ),
                delimiter=" ",
                ordering="duty_expression__sid",
            ),
        )
        return duty_sentence.get("duty_sentence", "")


class MeasuresQuerySet(TrackedModelQuerySet, ValidityQuerySet):
    def with_validity_field(self):
        return self.with_effective_valid_between()

    def with_effective_valid_between(self):
        """
        There are five ways in which measures can get end dated:

        1. Where the measure is given an explicit end date on the measure record
           itself
        2. Where the measure's generating regulation is a base regulation, and
           the base regulation itself is end-dated
        3. Where the measure's generating regulation is a modification
           regulation, and the modification regulation itself is end-dated
        4. Where the measure's generating regulation is a base regulation,
           and any of the modification regulations that modify it are end-dated
        5. Where the measure's generating regulation is a modification
           regulation, and the base regulation that it modifies is end-dated

        Numbers 2–5 also have to take account of the "effective end date" which
        if set should be used over any explicit date. The effective end date is
        set when other types of regulations are used (abrogation, prorogation,
        etc).
        """

        # Computing the end date for case 4 is expensive because it involves
        # aggregating over all of the modifications to the base regulation,
        # where there is one. So we pull this out into a CTE to let Postgres
        # know that none of this caluclation depends on the queryset filters.
        #
        # We also turn NULLs into "infinity" such that they sort to the top:
        # i.e. if any modification regulation is open-ended, so is the measure.
        # We then turn infinity back into NULL to be used in the date range.
        Regulation = self.model._meta.get_field(
            "generating_regulation",
        ).remote_field.model

        end_date_from_modifications = With(
            Regulation.objects.annotate(
                amended_end_date=NullIf(
                    Max(
                        Coalesce(
                            F("amendments__enacting_regulation__effective_end_date"),
                            EndDate("amendments__enacting_regulation__valid_between"),
                            Cast(Value("infinity"), DateField()),
                        ),
                    ),
                    Cast(Value("infinity"), DateField()),
                ),
            ),
            "end_date_from_modifications",
        )

        return (
            end_date_from_modifications.join(
                self,
                generating_regulation_id=end_date_from_modifications.col.id,
            )
            .with_cte(end_date_from_modifications)
            .annotate(
                db_effective_end_date=Coalesce(
                    # Case 1 – explicit end date, which is always used if present
                    EndDate("valid_between"),
                    # Case 2 and 3 – end date of regulation
                    F("generating_regulation__effective_end_date"),
                    EndDate("generating_regulation__valid_between"),
                    # Case 4 – generating regulation is a base regulation, and
                    # the modification regulation is end-dated
                    end_date_from_modifications.col.amended_end_date,
                    # Case 5 – generating regulation is a modification regulation,
                    # and the base it modifies is end-dated. Note that the above
                    # means that this only applies if the modification has no end date.
                    F("generating_regulation__amends__effective_end_date"),
                    EndDate("generating_regulation__amends__valid_between"),
                ),
                db_effective_valid_between=Func(
                    StartDate("valid_between"),
                    F("db_effective_end_date"),
                    Value("[]"),
                    function="DATERANGE",
                    output_field=TaricDateRangeField(),
                ),
            )
        )


class MeasureConditionQuerySet(TrackedModelQuerySet):
    def with_reference_price_string(self):
        """
        Returns a MeasureCondition queryset annotated with
        ``reference_price_string`` query expression.

        This expression should evaluate to a valid reference price string
        (https://uktrade.github.io/tariff-data-manual/documentation/data-structures/measure-conditions.html#condition-codes)

        If a condition has no duty_amount value, then this expression evaluates to an empty string value ("").
        Else it returns the result of three Case() expressions chained together.
        The first Case() expression evaluates to "%" if the condition has a duty amount and no monetary unit,
        else " ".

        The second evaluates to "" when a condition has no condition_measurement
        or its measurement has no measurement unit or the measurement unit has no abbreviation,
        else, if it has no monetary unit, the measurement unit abbreviation is returned,
        else, if it has a monetary unit, the abbreviation is returned prefixed by " / ".

        The third evaluates to "" when a measurement unit qualifier has no abbreviation,
        else the unit qualifier abbreviation is returned prefixed by " / ".
        """
        return self.annotate(
            reference_price_string=Case(
                When(
                    duty_amount__isnull=True,
                    then=Value(""),
                ),
                default=Concat(
                    "duty_amount",
                    Case(
                        When(
                            monetary_unit=None,
                            duty_amount__isnull=False,
                            then=Value("%"),
                        ),
                        default=Concat(
                            Value(" "),
                            F("monetary_unit__code"),
                        ),
                    ),
                    Case(
                        When(
                            Q(condition_measurement__isnull=True)
                            | Q(
                                condition_measurement__measurement_unit__isnull=True,
                            )
                            | Q(
                                condition_measurement__measurement_unit__abbreviation__isnull=True,
                            ),
                            then=Value(""),
                        ),
                        When(
                            monetary_unit__isnull=True,
                            then=F(
                                "condition_measurement__measurement_unit__abbreviation",
                            ),
                        ),
                        default=Concat(
                            Value(" / "),
                            F(
                                "condition_measurement__measurement_unit__abbreviation",
                            ),
                        ),
                    ),
                    Case(
                        When(
                            condition_measurement__measurement_unit_qualifier__abbreviation__isnull=True,
                            then=Value(""),
                        ),
                        default=Concat(
                            Value(" / "),
                            F(
                                "condition_measurement__measurement_unit_qualifier__abbreviation",
                            ),
                        ),
                    ),
                    output_field=CharField(),
                ),
            ),
        )
