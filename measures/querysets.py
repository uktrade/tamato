from django.contrib.postgres.aggregates import StringAgg
from django.db.models import Case
from django.db.models import CharField
from django.db.models import F
from django.db.models import Func
from django.db.models import Q
from django.db.models import QuerySet
from django.db.models import Value
from django.db.models import When
from django.db.models.aggregates import Max
from django.db.models.fields import DateField
from django.db.models.functions import Coalesce
from django.db.models.functions import Concat
from django.db.models.functions.comparison import Cast
from django.db.models.functions.comparison import NullIf
from django.db.models.functions.text import Trim
from django_cte.cte import With

from common.fields import TaricDateRangeField
from common.models.tracked_qs import TrackedModelQuerySet
from common.util import EndDate
from common.util import StartDate
from regulations.models import Regulation


class DutySentenceMixin(QuerySet):
    def with_duty_sentence(self) -> QuerySet:
        """
        Annotates the query set with a human-readable string that represents the
        aggregation of all of the linked components into a single duty sentence.

        This operation relies on the `prefix` and `abbreviation` fields being
        filled in on duty expressions and units, which are not supplied by the
        TARIC3 XML by default.

        Strings output by this annotation should be valid input to the
        :class:`~measures.parsers.DutySentenceParser`.

        The annotated field will be generated using the below SQL:

        .. code:: SQL

            STRING_AGG(
              TRIM(
                CONCAT(
                  CASE
                    WHEN (
                      "measures_dutyexpression"."prefix" IS NULL
                      OR "measures_dutyexpression"."prefix" = ''
                    ) THEN
                    ELSE CONCAT("measures_dutyexpression"."prefix",' ')
                  END,
                  CONCAT(
                    "measures_measureconditioncomponent"."duty_amount",
                    CONCAT(
                      CASE
                        WHEN (
                          "measures_measureconditioncomponent"."duty_amount" IS NOT NULL
                          AND "measures_measureconditioncomponent"."monetary_unit_id" IS NULL
                        ) THEN '%'
                        WHEN "measures_measureconditioncomponent"."duty_amount" IS NULL THEN ''
                        ELSE CONCAT(' ', "measures_monetaryunit"."code")
                      END,
                      CONCAT(
                        CASE
                          WHEN "measures_measurementunit"."abbreviation" IS NULL THEN ''
                          WHEN "measures_measureconditioncomponent"."monetary_unit_id" IS NULL THEN "measures_measurementunit"."abbreviation"
                          ELSE CONCAT(' / ', "measures_measurementunit"."abbreviation")
                        END,
                        CASE
                          WHEN "measures_measurementunitqualifier"."abbreviation" IS NULL THEN
                          ELSE CONCAT(
                            ' / ',
                            "measures_measurementunitqualifier"."abbreviation"
                          )
                        END
                      )
                    )
                  )
                )
              ),
            ) AS "duty_sentence"
        """
        return self.annotate(
            duty_sentence=StringAgg(
                expression=Trim(
                    Concat(
                        Case(
                            When(
                                Q(components__duty_expression__prefix__isnull=True)
                                | Q(components__duty_expression__prefix=""),
                                then=Value(""),
                            ),
                            default=Concat(
                                F("components__duty_expression__prefix"),
                                Value(" "),
                            ),
                        ),
                        "components__duty_amount",
                        Case(
                            When(
                                components__monetary_unit=None,
                                components__duty_amount__isnull=False,
                                then=Value("%"),
                            ),
                            When(
                                components__duty_amount__isnull=True,
                                then=Value(""),
                            ),
                            default=Concat(
                                Value(" "),
                                F("components__monetary_unit__code"),
                            ),
                        ),
                        Case(
                            When(
                                Q(components__component_measurement=None)
                                | Q(
                                    components__component_measurement__measurement_unit=None,
                                )
                                | Q(
                                    components__component_measurement__measurement_unit__abbreviation=None,
                                ),
                                then=Value(""),
                            ),
                            When(
                                components__monetary_unit__isnull=True,
                                then=F(
                                    "components__component_measurement__measurement_unit__abbreviation",
                                ),
                            ),
                            default=Concat(
                                Value(" / "),
                                F(
                                    "components__component_measurement__measurement_unit__abbreviation",
                                ),
                            ),
                        ),
                        Case(
                            When(
                                components__component_measurement__measurement_unit_qualifier__abbreviation=None,
                                then=Value(""),
                            ),
                            default=Concat(
                                Value(" / "),
                                F(
                                    "components__component_measurement__measurement_unit_qualifier__abbreviation",
                                ),
                            ),
                        ),
                        output_field=CharField(),
                    ),
                ),
                delimiter=" ",
                ordering="components__duty_expression__sid",
            ),
        )


class MeasuresQuerySet(TrackedModelQuerySet, DutySentenceMixin):
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


class MeasureConditionQuerySet(TrackedModelQuerySet, DutySentenceMixin):
    def with_reference_price_string(self):
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
                            monetary_unit__isnull=True,
                            then=Value(""),
                        ),
                        default=Concat(
                            Value(" "),
                            F("monetary_unit__code"),
                        ),
                    ),
                    Case(
                        When(
                            condition_measurement__measurement_unit__code__isnull=True,
                            then=Value(""),
                        ),
                        default=Concat(
                            Value(" "),
                            F("condition_measurement__measurement_unit__code"),
                        ),
                    ),
                    Case(
                        When(
                            condition_measurement__measurement_unit_qualifier__code__isnull=True,
                            then=Value(""),
                        ),
                        default=Concat(
                            Value(" "),
                            F(
                                "condition_measurement__measurement_unit_qualifier__code",
                            ),
                        ),
                    ),
                    output_field=CharField(),
                ),
            ),
        )
