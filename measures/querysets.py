from django.contrib.postgres.aggregates import StringAgg
from django.db.models import Case
from django.db.models import CharField
from django.db.models import F
from django.db.models import Func
from django.db.models import Q
from django.db.models import QuerySet
from django.db.models import Value
from django.db.models import When
from django.db.models.functions import Concat
from django.db.models.functions.text import Trim

from common.fields import TaricDateRangeField
from common.models.tracked_qs import TrackedModelQuerySet


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
        In many cases the measures regulation effective_end_date overrides the
        measures validity range.

        Annotate the queryset with the db_effective_valid_between based on the regulations and measure.

        Generates the following SQL:

        .. code:: SQL

            SELECT *,
                   CASE
                     WHEN (
                       "regulations_regulation"."effective_end_date" IS NOT NULL AND
                       "measures_measure"."valid_between" @> "regulations_regulation"."effective_end_date"::timestamp WITH time zone AND
                       NOT Upper_inf("measures_measure"."valid_between")
                     ) THEN Daterange(Lower("measures_measure"."valid_between"), "regulations_regulation"."effective_end_date", [])
                     WHEN (
                       "regulations_regulation"."effective_end_date" IS NOT NULL AND
                       Upper_inf("measures_measure"."valid_between")
                     ) THEN "measures_measure"."valid_between"
                     WHEN (
                       "measures_measure"."terminating_regulation_id" IS NOT NULL AND
                       NOT Upper_inf("measures_measure"."valid_between")
                     ) THEN "measures_measure"."valid_between"
                     WHEN "measures_measure"."generating_regulation_id" IS NOT NULL THEN Daterange(Lower("measures_measure"."valid_between"), "regulations_regulation"."effective_end_date", [])
                     ELSE "measures_measure"."valid_between"
                   END AS "db_effective_valid_between"
              FROM "measures_measure"
             INNER JOIN "regulations_regulation"
                ON "measures_measure"."generating_regulation_id" = "regulations_regulation"."trackedmodel_ptr_id"
             INNER JOIN "common_trackedmodel"
                ON "measures_measure"."trackedmodel_ptr_id" = "common_trackedmodel"."id"
        """
        return self.annotate(
            db_effective_valid_between=Case(
                When(
                    valid_between__upper_inf=False,
                    generating_regulation__effective_end_date__isnull=False,
                    valid_between__contains=F(
                        "generating_regulation__effective_end_date",
                    ),
                    then=Func(
                        Func(F("valid_between"), function="LOWER"),
                        F("generating_regulation__effective_end_date"),
                        Value("[]"),
                        function="DATERANGE",
                    ),
                ),
                When(
                    valid_between__upper_inf=False,
                    generating_regulation__effective_end_date__isnull=False,
                    then=F("valid_between"),
                ),
                When(
                    valid_between__upper_inf=False,
                    terminating_regulation__isnull=False,
                    then=F("valid_between"),
                ),
                When(
                    generating_regulation__isnull=False,
                    then=Func(
                        Func(F("valid_between"), function="LOWER"),
                        F("generating_regulation__effective_end_date"),
                        Value("[]"),
                        function="DATERANGE",
                    ),
                ),
                default=F("valid_between"),
                output_field=TaricDateRangeField(),
            ),
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
