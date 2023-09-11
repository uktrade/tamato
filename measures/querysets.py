from typing import Union

from django.contrib.postgres.aggregates import StringAgg
from django.db.models import Case
from django.db.models import CharField
from django.db.models import F
from django.db.models import Func
from django.db.models import Q
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

import measures
from common.fields import TaricDateRangeField
from common.models.tracked_qs import TrackedModelQuerySet
from common.querysets import ValidityQuerySet
from common.util import EndDate
from common.util import StartDate


from django.db.models import Value, Case, CharField, When, F

class ComponentQuerySet(TrackedModelQuerySet):

    def duty_sentence(self, component_parent):
        # Get the "current" components based on transaction_id.
        component_qs = component_parent.components.approved_up_to_transaction(
            component_parent.transaction,
        )

        if not component_qs:
            return ""

        # Get the latest transaction_id.
        latest_transaction_id = component_qs.aggregate(
            latest_transaction_id=Max("transaction_id"),
        ).get("latest_transaction_id")

        # Filter components by the latest transaction_id.
        component_qs = component_qs.filter(transaction_id=latest_transaction_id)

        # Construct the duty sentence.
        duty_sentence = component_qs.annotate(
            prefix_value=Case(
                When(
                    trackedmodel_ptr_id__isnull=True,
                    then=Value(""),
                ),
                default=F('duty_expression__prefix'),
                output_field=CharField(),
            ),
            monetary_unit_value=Case(
                When(
                    Q(duty_amount__isnull=False) & Q(monetary_unit=None),
                    then=Value("%"),
                ),
                When(duty_amount__isnull=True, then=Value("")),
                default=Value(" "),
                output_field=CharField(),
            ),
        ).annotate(
            full_sentence=Trim(
                Concat(
                    'prefix_value',
                    Value(" "),
                    F('duty_expression__monetary_unit_applicability_code'),
                    Value(" / "),
                    F('component_measurement__measurement_unit__abbreviation'),
                    Value(" / "),
                    F('component_measurement__measurement_unit_qualifier__abbreviation'),
                ),
                output_field=CharField(),
            )
        ).aggregate(
            duty_sentence=StringAgg(
                'full_sentence',
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
        return self.select_related("monetary_unit", "condition_measurement__measurement_unit",
                                   "condition_measurement__measurement_unit_qualifier").annotate(
            reference_price_string=Case(
                When(
                    duty_amount__isnull=True,
                    then=Value(""),
                ),
                default=Concat(
                    F("duty_amount"),
                    Case(
                        When(
                            monetary_unit=None,
                            duty_amount__isnull=False,
                            then=Value("%"),
                        ),
                        default=Value(" "),  # Space separator
                        output_field=CharField(),
                    ),
                    F("monetary_unit__code"),
                    Case(
                        When(
                            condition_measurement__isnull=True
                                                          | F("condition_measurement__measurement_unit__isnull")
                                                          | F(
                                "condition_measurement__measurement_unit__abbreviation__isnull"),
                            then=Value(""),
                        ),
                        default=Value(" / "),
                        output_field=CharField(),
                    ),
                    F("condition_measurement__measurement_unit__abbreviation"),
                    Case(
                        When(
                            condition_measurement__measurement_unit_qualifier__abbreviation__isnull=True,
                            then=Value(""),
                        ),
                        default=Value(" / "),
                        output_field=CharField(),
                    ),
                    F("condition_measurement__measurement_unit_qualifier__abbreviation"),
                    output_field=CharField(),
                ),
                output_field=CharField(),
            ),
        )
