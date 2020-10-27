from decimal import Decimal

from django.contrib.postgres.fields import JSONField
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models

from common.models import ShortDescription
from common.models import SignedIntSID
from common.models import TrackedModel
from common.models import ValidityMixin
from quotas import validators


class QuotaOrderNumber(TrackedModel, ValidityMixin):
    """The order number is the identification of a quota. It is defined for tariff
    quotas and surveillances. If an operator wants to benefit from a tariff quota, they
    must refer to it via the order number in the customs declaration. An order number
    may have multiple associated quota definitions, for example to divide a quota over
    several time periods.
    """

    record_code = "360"
    subrecord_code = "00"

    sid = SignedIntSID()
    order_number = models.CharField(
        max_length=6, validators=[validators.quota_order_number_validator]
    )
    mechanism = models.PositiveSmallIntegerField(
        choices=validators.AdministrationMechanism.choices
    )
    category = models.PositiveSmallIntegerField(
        choices=validators.QuotaCategory.choices
    )

    origins = models.ManyToManyField(
        "geo_areas.GeographicalArea",
        through="QuotaOrderNumberOrigin",
        related_name="quotas",
    )

    def __str__(self):
        return self.order_number

    def clean(self):
        validators.validate_unique_id_and_start_date(self)

    def validate_workbasket(self):
        validators.validate_no_overlapping_quota_order_numbers(self)

    def delete(self):
        validators.validate_order_number_used_in_measure_cannot_be_deleted(self)
        super().delete()


class QuotaOrderNumberOrigin(TrackedModel, ValidityMixin):
    """The order number origin defines a quota as being available only to imports from a
    specific origin, usually a country or group of countries.
    """

    record_code = "360"
    subrecord_code = "10"

    sid = SignedIntSID()
    order_number = models.ForeignKey(QuotaOrderNumber, on_delete=models.PROTECT)
    geographical_area = models.ForeignKey(
        "geo_areas.GeographicalArea", on_delete=models.PROTECT
    )

    excluded_areas = models.ManyToManyField(
        "geo_areas.GeographicalArea",
        through="QuotaOrderNumberOriginExclusion",
        related_name="+",
    )

    def clean(self):
        validators.validate_geo_area_validity_spans_origin_validity(self)

    def validate_workbasket(self):
        validators.validate_no_overlapping_quota_order_number_origins(self)
        validators.validate_order_number_validity_spans_origin_validity(self)
        validators.validate_origin_validity_spans_measure_validity(self)

    def delete(self):
        validators.validate_origin_used_in_measure_cannot_be_deleted(self)
        super().delete()


class QuotaOrderNumberOriginExclusion(TrackedModel):
    """Origin exclusions specify countries (or groups of countries, or other origins) to
    exclude from the quota number origin.
    """

    record_code = "360"
    subrecord_code = "15"

    origin = models.ForeignKey(QuotaOrderNumberOrigin, on_delete=models.PROTECT)
    excluded_geographical_area = models.ForeignKey(
        "geo_areas.GeographicalArea", on_delete=models.PROTECT
    )

    identifying_fields = "origin", "excluded_geographical_area"

    def validate_workbasket(self):
        validators.validate_exclusion_only_from_group_origin(self)
        validators.validate_excluded_geo_area_must_be_member_of_origin_group(self)


class QuotaDefinition(TrackedModel, ValidityMixin):
    """Defines the validity period and quantity for which a quota is applicable. This
    model also represents sub-quotas, via a parent-child recursive relation through
    QuotaAssociation.

    The monetary unit code and the measurement unit code (with its optional unit
    qualifier code) are mutually exclusive.
    """

    record_code = "370"
    subrecord_code = "00"

    sid = SignedIntSID()
    order_number = models.ForeignKey(QuotaOrderNumber, on_delete=models.PROTECT)
    volume = models.DecimalField(max_digits=14, decimal_places=3)
    initial_volume = models.DecimalField(max_digits=14, decimal_places=3)
    monetary_unit = models.ForeignKey(
        "measures.MonetaryUnit",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    measurement_unit = models.ForeignKey(
        "measures.MeasurementUnit",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    measurement_unit_qualifier = models.ForeignKey(
        "measures.MeasurementUnitQualifier",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    maximum_precision = models.PositiveSmallIntegerField(
        validators=[validators.validate_max_precision]
    )
    quota_critical = models.BooleanField(default=False)
    # the percentage at which the quota becomes critical
    quota_critical_threshold = models.PositiveSmallIntegerField(
        validators=[validators.validate_percentage]
    )
    description = ShortDescription()

    sub_quotas = models.ManyToManyField(
        "self", through="QuotaAssociation", through_fields=("main_quota", "sub_quota")
    )

    def __str__(self):
        return self.description

    def clean(self):
        validators.validate_monetary_unit_validity_spans_definition_validity(self)
        validators.validate_measurement_unit_validity_spans_definition_validity(self)
        validators.validate_measurement_unit_qualifier_validity_spans_definition_validity(
            self
        )

    def validate_workbasket(self):
        validators.validate_unique_order_number_and_start_date(self)
        validators.validate_order_number_validity_spans_quota_definition_validity(self)


class QuotaAssociation(TrackedModel):
    """The quota association defines the relation between quota and sub-quotas."""

    record_code = "370"
    subrecord_code = "05"

    main_quota = models.ForeignKey(
        QuotaDefinition, on_delete=models.PROTECT, related_name="sub_quota_associations"
    )
    sub_quota = models.ForeignKey(
        QuotaDefinition,
        on_delete=models.PROTECT,
        related_name="main_quota_associations",
    )
    sub_quota_relation_type = models.CharField(
        max_length=2, choices=validators.SubQuotaType.choices
    )
    coefficient = models.DecimalField(
        max_digits=16,
        decimal_places=5,
        default=Decimal("1.00000"),
        validators=[validators.validate_coefficient],
    )
    identifying_fields = ("main_quota", "sub_quota")

    def validate_workbasket(self):
        validators.validate_unique_quota_association(self)
        validators.validate_sub_quota_validity_enclosed_by_main_quota_validity(self)
        validators.validate_equivalent_subquotas(self)
        validators.validate_normal_subquotas(self)
        validators.validate_sub_quotas_have_same_type(self)


class QuotaSuspension(TrackedModel, ValidityMixin):
    """Defines a suspension period for a quota."""

    record_code = "370"
    subrecord_code = "15"

    sid = SignedIntSID()
    quota_definition = models.ForeignKey(QuotaDefinition, on_delete=models.PROTECT)
    description = ShortDescription()

    def __str__(self):
        return self.description

    def validate_workbasket(self):
        validators.validate_suspension_only_on_fcfs_quotas(self)
        validators.validate_suspension_period(self)


class QuotaBlocking(TrackedModel, ValidityMixin):
    """Defines a blocking period for a (sub-)quota."""

    record_code = "370"
    subrecord_code = "10"

    sid = SignedIntSID()
    quota_definition = models.ForeignKey(QuotaDefinition, on_delete=models.PROTECT)
    blocking_period_type = models.PositiveSmallIntegerField(
        choices=validators.BlockingPeriodType.choices
    )
    description = ShortDescription()

    def validate_workbasket(self):
        validators.validate_blocking_only_on_fcfs_quotas(self)
        validators.validate_blocking_period_start_date(self)


class QuotaEvent(TrackedModel):
    """We do not care about quota events, except to store historical data. So this model
    stores all events in a single table."""

    record_code = "375"
    subrecord_code = models.CharField(
        max_length=2, choices=validators.QuotaEventType.choices
    )
    quota_definition = models.ForeignKey(QuotaDefinition, on_delete=models.PROTECT)
    occurrence_timestamp = models.DateTimeField()
    # store the event-type specific data in a JSON object
    data = JSONField(default=dict, encoder=DjangoJSONEncoder)

    identifying_fields = ("subrecord_code", "quota_definition")
