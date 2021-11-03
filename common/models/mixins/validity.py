from datetime import date
from datetime import timedelta
from typing import TypeVar

from django.conf import settings
from django.db import models
from django.db.models import aggregates
from django.db.models import expressions
from django.db.models import functions
from django.db.models.fields import DateField
from django_cte import CTEQuerySet
from django_cte.cte import With

from common.fields import TaricDateRangeField
from common.util import TaricDateRange
from common.validators import UpdateType

Self = TypeVar("Self", bound="ValidityMixin")


class ValidityMixin(models.Model):
    """
    The model is live after the validity start date
    (:attr:`valid_between.lower`) and before the validity end date
    (:attr:`valid_between.upper`).

    Start and end validity dates are inclusive – meaning that the model is live
    from the beginning of the start date to the end of the end date. A model
    with the same start and end date is therefore live for 1 day. If the
    validity end date is blank (:attr:`valid_between.upper_inf`) then the model
    is live indefinitely after the start date.

    Validity dates can be modified with a new version of a model, so a model
    that initially has a blank end date can be updated to subsequently add one.
    """

    if settings.SQLITE:
        validity_start = DateField(db_index=True, null=True, blank=True)
        validity_end = DateField(db_index=True, null=True, blank=True)
    else:
        valid_between = TaricDateRangeField(db_index=True)

    validity_field_name: str = "valid_between"
    """The name of the field that should be used for validity date checking."""

    @classmethod
    def objects_with_validity_field(cls):
        """
        Returns a QuerySet which will have this model's validity date field (as
        specified by :attr:`validity_field_name`) present on the returned
        models.

        The need for this is that some models (e.g.
        :class:`~measures.models.Measure`) use a validity date that is computed
        on demand as part of a database query and hence is not present on the
        default queryset.
        """
        return cls.objects

    def terminate(self: Self, workbasket, when: date, **params) -> Self:
        """
        Returns a new version of the object updated to end on the specified
        date.

        If the object would not have started on that date, the object is deleted
        instead. If the object will already have ended by this date, then does
        nothing.

        Any keyword arguments passed will be applied in the case of an update
        and are ignored for a delete or no change.
        """
        starts_after_date = (
            not self.valid_between.lower_inf and self.valid_between.lower >= when
        )
        ends_before_date = (
            not self.valid_between.upper_inf and self.valid_between.upper < when
        )

        if ends_before_date:
            return self

        update_params = {}
        if starts_after_date:
            update_params["update_type"] = UpdateType.DELETE
        else:
            update_params["update_type"] = UpdateType.UPDATE
            update_params["valid_between"] = TaricDateRange(
                lower=self.valid_between.lower,
                upper=when,
            )
            update_params.update(params)

        return self.new_version(workbasket, **update_params)

    class Meta:
        abstract = True


class ValidityStartQueryset(CTEQuerySet):
    def with_end_date(self):
        """
        Returns a :class:`QuerySet` where the :attr:`validity_end` date and the
        :attr:`valid_between` date range have been annotated onto the query.

        The resulting annotations can be queried on like fully materialised
        fields. E.g, it is possible to filter on the `valid_between` field.

        .. code-block:: python

            Model.objects.with_end_date().filter(
                valid_between__contains=date.today(),
            )
        """

        # Models with a single validity date always represent some feature of a
        # "parent model" and are only live for as long as that model is live.
        # The `over_field` is the field on this model that is a foreign key to
        # the "parent model". E.g. for a description it is the described model.
        over_field = self.model._meta.get_field(self.model.validity_over)

        # When we are working out the validity of the next mdoel, only models
        # for the same "parent model" are considered. So this partition selects
        # only the models that match on the same parent fields.
        partition = [
            models.F(f"{over_field.name}__{field}")
            for field in over_field.related_model.identifying_fields
        ]

        # To work out the end date efficiently an SQL window expression is used.
        # The rule for models with only a validity start date is that they are
        # valid up until the next model takes over. So this is the same as
        # ordering the models by their start dates and then takeing the start
        # date of the model that appears after this one.
        window = expressions.Window(
            expression=aggregates.Max("validity_start"),
            partition_by=partition,
            order_by=models.F("validity_start").asc(),
            frame=expressions.RowRange(start=0, end=1),
        )

        # If the value returned by the window expression is the same as the
        # model's own start date, that means there was no future model with a
        # later start date. Hence, this model is at the moment valid for
        # unlimited time. NULLIF returns NULL if the two values match. A day has
        # to be subtracted from the final result because the end date is one day
        # before the next start date.
        end_date_field = functions.Cast(
            functions.NullIf(window, models.F("validity_start")) - timedelta(days=1),
            models.DateField(),
        )

        # To allow the resulting field to be queried, this must be done as part
        # of a Common Table Expression (CTE) because window expressions cannot
        # appear in a WHERE clause.
        #
        # The end date and the start date are combined together into a single
        # DATERANGE field to allow using __contains operators.
        with_dates_added = With(
            self.annotate(
                validity_end=end_date_field,
                valid_between=models.Func(
                    models.F("validity_start"),
                    models.F("validity_end"),
                    expressions.Value("[]"),
                    function="DATERANGE",
                    output_field=TaricDateRangeField(),
                ),
            ),
        )

        return (
            with_dates_added.join(self.model, pk=with_dates_added.col.pk)
            .with_cte(with_dates_added)
            .annotate(
                validity_end=with_dates_added.col.validity_end,
                valid_between=with_dates_added.col.valid_between,
            )
        )


class ValidityStartMixin(models.Model):
    """
    The model is live after the :attr:`validity_start` date and before the
    :attr:`validity_start` date of the next model in the same series.

    This is broadly the same as the :class:`~common.models.mixins.ValidityMixin`
    but the lack of an end date enforces that there is always one model of this
    type active at any one time for a given series.

    This validity method is used when this model tracks some time-varying
    property of a related model. For example, this model may carry a description
    of the related model, and the description can be updated independently of
    the related model. The "series" is then defined by
    :attr:`~common.models.TrackedModel.identifing_fields` of the related model,
    such that for each related model there can be multiple of this model, each
    with their own validity period.

    Start and end validity dates are inclusive – meaning that the model is live
    from the beginning of the start date to the end of the end date. A model
    with the same start and end date is therefore live for 1 day. If the
    validity end date is blank then the model is live indefinitely after the
    start date.
    """

    validity_start = models.DateField(db_index=True, null=False, blank=False)

    validity_over: str
    """Models with a single validity date always represent some feature of a
    related model and are only live for as long as that model is live. The is
    the name of the field on this model that is a foreign key to the related
    model. E.g. for a description it is the described model."""

    objects: ValidityStartQueryset
    """The :meth:`~common.models.mixins.ValidityStartQuerySet.with_end_date`
    method is used to automatically compute the end date based on the other
    models in the series. """

    @classmethod
    def objects_with_validity_field(cls):
        """
        Returns a QuerySet which will have this model's validity date range
        present on the returned models.

        The need for this is that ValidityStart models use a validity date range
        that is computed on demand as part of a database query and hence is not
        present on the default queryset.
        """
        return cls.objects.with_end_date()

    class Meta:
        abstract = True
