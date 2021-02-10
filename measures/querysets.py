from django.db.models import Case
from django.db.models import F
from django.db.models import Func
from django.db.models import Value
from django.db.models import When

from common.fields import TaricDateRangeField
from common.models.records import TrackedModelQuerySet


class MeasuresQuerySet(TrackedModelQuerySet):
    def with_effective_valid_between(self):
        """
        In many cases the measures regulation effective_end_date overrides the measures validity range.

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
                        "generating_regulation__effective_end_date"
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
            )
        )
