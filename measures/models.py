from datetime import datetime
from datetime import timezone

from django.db import models
from polymorphic.managers import PolymorphicManager

from common.fields import ApplicabilityCode
from common.fields import ShortDescription
from common.fields import SignedIntSID
from common.models import TrackedModel
from common.models import ValidityMixin
from common.util import TaricDateTimeRange
from measures import business_rules
from measures import validators
from measures.querysets import MeasuresQuerySet
from quotas.validators import quota_order_number_validator


class MeasureTypeSeries(TrackedModel, ValidityMixin):
    """Measure types may be grouped into series. The series can be used to determine how
    duties are applied, and the possible cumulative effect of other applicable
    measures.
    """

    record_code = "140"
    subrecord_code = "00"

    description_record_code = "140"
    description_subrecord_code = "05"

    sid = models.CharField(
        max_length=2,
        validators=[validators.measure_type_series_id_validator],
        db_index=True,
    )
    measure_type_combination = models.PositiveSmallIntegerField(
        choices=validators.MeasureTypeCombination.choices
    )
    description = ShortDescription()

    business_rules = (
        business_rules.MTS1,
        business_rules.MTS2,
    )

    def in_use(self):
        # TODO handle deletes
        return MeasureType.objects.filter(
            measure_type_series__sid=self.sid,
        ).exists()


class MeasurementUnit(TrackedModel, ValidityMixin):
    """The measurement unit refers to the ISO measurement unit code."""

    record_code = "210"
    subrecord_code = "00"

    description_record_code = "210"
    description_subrecord_code = "05"

    code = models.CharField(
        max_length=3,
        validators=[validators.measurement_unit_code_validator],
        db_index=True,
    )
    description = ShortDescription()
    abbreviation = models.CharField(max_length=32, blank=True)

    identifying_fields = ("code",)
    business_rules = (
        business_rules.MT1,
        business_rules.MT3,
        business_rules.MT4,
        business_rules.MT7,
        business_rules.MT10,
    )


class MeasurementUnitQualifier(TrackedModel, ValidityMixin):
    """The measurement unit qualifier is used to qualify a measurement unit. For example
    the measurement unit "kilogram" may be qualified as "net" or "gross".
    """

    record_code = "215"
    subrecord_code = "00"

    description_record_code = "215"
    description_subrecord_code = "05"

    code = models.CharField(
        max_length=1,
        validators=[validators.measurement_unit_qualifier_code_validator],
        db_index=True,
    )
    description = ShortDescription()
    abbreviation = models.CharField(max_length=32, blank=True)

    identifying_fields = ("code",)


class Measurement(TrackedModel, ValidityMixin):
    """The measurement defines the relationship between a measurement unit and a
    measurement unit qualifier. This avoids meaningless combinations of the measurement
    unit and the measurement unit qualifier. Unlike in the TARIC model, we put all combinations
    of measurement in this table including ones where the qualifier is null.
    These do not appear in output XML.
    """

    record_code = "220"
    subrecord_code = "00"

    measurement_unit = models.ForeignKey("MeasurementUnit", on_delete=models.PROTECT)
    measurement_unit_qualifier = models.ForeignKey(
        "MeasurementUnitQualifier",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )

    identifying_fields = ("measurement_unit", "measurement_unit_qualifier")


class MonetaryUnit(TrackedModel, ValidityMixin):
    """The monetary unit identifies the currency code used in the system."""

    record_code = "225"
    subrecord_code = "00"

    description_record_code = "225"
    description_subrecord_code = "05"

    code = models.CharField(
        max_length=3,
        validators=[validators.monetary_unit_code_validator],
        db_index=True,
    )
    description = ShortDescription()

    identifying_fields = ("code",)


class DutyExpression(TrackedModel, ValidityMixin):
    """The duty expression identifies the type of duty which must be applied for a given
    measure component. It will also control how the duty will be expressed, for example
    whether an amount is "permitted" or "mandatory".
    """

    record_code = "230"
    subrecord_code = "00"

    description_record_code = "230"
    description_subrecord_code = "05"

    sid = models.IntegerField(
        choices=validators.DutyExpressionId.choices, db_index=True
    )
    prefix = models.CharField(max_length=14, blank=True)
    duty_amount_applicability_code = ApplicabilityCode()
    measurement_unit_applicability_code = ApplicabilityCode()
    monetary_unit_applicability_code = ApplicabilityCode()
    description = ShortDescription()


class MeasureType(TrackedModel, ValidityMixin):
    """The measure type identifies a customs measure. TARIC customs measures cover a
    wide range of information, including tariff measures (such as levies and
    anti-dumping duties), and non-tariff measures (such as quantitative restrictions
    and prohibitions).
    """

    record_code = "235"
    subrecord_code = "00"

    description_record_code = "235"
    description_subrecord_code = "05"

    sid = models.CharField(
        max_length=6, validators=[validators.measure_type_id_validator], db_index=True
    )
    trade_movement_code = models.PositiveSmallIntegerField(
        choices=validators.ImportExportCode.choices
    )
    priority_code = models.PositiveSmallIntegerField(
        validators=[validators.validate_priority_code]
    )
    measure_component_applicability_code = ApplicabilityCode()
    origin_destination_code = models.PositiveSmallIntegerField(
        choices=validators.ImportExportCode.choices
    )
    order_number_capture_code = models.PositiveSmallIntegerField(
        choices=validators.OrderNumberCaptureCode.choices
    )
    measure_explosion_level = models.PositiveSmallIntegerField(
        choices=validators.MeasureExplosionLevel.choices,
        validators=[validators.validate_measure_explosion_level],
    )
    description = ShortDescription()
    measure_type_series = models.ForeignKey(MeasureTypeSeries, on_delete=models.PROTECT)

    additional_code_types = models.ManyToManyField(
        "additional_codes.AdditionalCodeType", through="AdditionalCodeTypeMeasureType"
    )

    def in_use(self):
        # TODO handle deletes
        return Measure.objects.filter(measure_type__sid=self.sid).exists()

    @property
    def components_mandatory(self):
        return (
            self.measure_component_applicability_code
            == validators.ApplicabilityCode.MANDATORY
        )

    @property
    def components_not_permitted(self):
        return (
            self.measure_component_applicability_code
            == validators.ApplicabilityCode.NOT_PERMITTED
        )

    @property
    def order_number_mandatory(self):
        return self.order_number_capture_code == validators.ApplicabilityCode.MANDATORY

    @property
    def order_number_not_permitted(self):
        return (
            self.order_number_capture_code == validators.ApplicabilityCode.NOT_PERMITTED
        )


class AdditionalCodeTypeMeasureType(TrackedModel, ValidityMixin):
    """The relation between an additional code type and a measure type ensures a
    coherent association between additional codes and measures.
    """

    record_code = "240"
    subrecord_code = "00"

    measure_type = models.ForeignKey(MeasureType, on_delete=models.PROTECT)
    additional_code_type = models.ForeignKey(
        "additional_codes.AdditionalCodeType", on_delete=models.PROTECT
    )

    identifying_fields = ("measure_type", "additional_code_type")


class MeasureConditionCode(TrackedModel, ValidityMixin):
    """A measure condition code identifies a broad area where conditions are required,
    for example "C" will have the description "required to present a certificate".
    """

    record_code = "350"
    subrecord_code = "00"

    description_record_code = "350"
    description_subrecord_code = "05"

    code = models.CharField(
        max_length=2,
        validators=[validators.measure_condition_code_validator],
        db_index=True,
    )
    description = ShortDescription()

    identifying_fields = ("code",)

    business_rules = (
        business_rules.MC1,
        business_rules.MC4,
    )

    def used_in_component(self):
        # TODO handle deletes
        # TODO handle MeasureConditionCode versions
        return MeasureConditionComponent.objects.filter(
            condition__condition_code__code=self.code,
        ).exists()


class MeasureAction(TrackedModel, ValidityMixin):
    """The measure action identifies the action to take when a given condition is met.
    For example, the description of "01" will be "apply ACTION AMOUNT".
    """

    record_code = "355"
    subrecord_code = "00"

    description_record_code = "355"
    description_subrecord_code = "05"

    code = models.CharField(
        max_length=3, validators=[validators.validate_action_code], db_index=True
    )
    description = ShortDescription()

    identifying_fields = ("code",)

    business_rules = (
        business_rules.MA1,
        business_rules.MA2,
    )

    def in_use(self):
        # TODO handle deletes
        return MeasureConditionComponent.objects.filter(
            condition__action__code=self.code,
        ).exists()


class Measure(TrackedModel, ValidityMixin):
    """Defines the validity period in which a particular measure type is applicable to
    particular nomenclature for a particular geographical area.

    Measures in the TARIC database are stored against the nomenclature code which is at the
    highest level appropriate in the hierarchy. Thus, measures which apply to all the
    declarable codes in a complete chapter are stored against the nomenclature code for the
    chapter (i.e. at the 2-digit level only); those which apply to all sub-divisions of an
    HS code are stored against that HS code (i.e. at the 6-digit level only). The advantage
    of this system is that it reduces the number of measures stored in the database; the
    data capture workload (thus diminishing the possibility of introducing errors) and the
    transmission volumes.
    """

    record_code = "430"
    subrecord_code = "00"

    sid = SignedIntSID(db_index=True)
    measure_type = models.ForeignKey(MeasureType, on_delete=models.PROTECT)
    geographical_area = models.ForeignKey(
        "geo_areas.GeographicalArea",
        on_delete=models.PROTECT,
        related_name="measures",
    )
    goods_nomenclature = models.ForeignKey(
        "commodities.GoodsNomenclature",
        on_delete=models.PROTECT,
        related_name="measures",
        null=True,
        blank=True,
    )
    additional_code = models.ForeignKey(
        "additional_codes.AdditionalCode",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    dead_additional_code = models.CharField(
        max_length=16, null=True, blank=True, db_index=True
    )
    order_number = models.ForeignKey(
        "quotas.QuotaOrderNumber", on_delete=models.PROTECT, null=True, blank=True
    )
    dead_order_number = models.CharField(
        max_length=6,
        validators=[quota_order_number_validator],
        null=True,
        blank=True,
        db_index=True,
    )
    reduction = models.PositiveSmallIntegerField(
        validators=[validators.validate_reduction_indicator],
        null=True,
        blank=True,
        db_index=True,
    )
    generating_regulation = models.ForeignKey(
        "regulations.Regulation", on_delete=models.PROTECT
    )
    terminating_regulation = models.ForeignKey(
        "regulations.Regulation",
        on_delete=models.PROTECT,
        related_name="terminated_measures",
        null=True,
        blank=True,
    )
    stopped = models.BooleanField(default=False)
    export_refund_nomenclature_sid = SignedIntSID(null=True, blank=True, default=None)

    footnotes = models.ManyToManyField(
        "footnotes.Footnote", through="FootnoteAssociationMeasure"
    )

    identifying_fields = ("sid",)

    business_rules = (
        business_rules.ME1,
        business_rules.ME2,
        business_rules.ME3,
        business_rules.ME4,
        business_rules.ME5,
        business_rules.ME6,
        business_rules.ME7,
        business_rules.ME8,
        business_rules.ME88,
        business_rules.ME16,
        business_rules.ME115,
        business_rules.ME25,
        business_rules.ME32,
        business_rules.ME10,
        business_rules.ME116,
        business_rules.ME119,
        business_rules.ME9,
        business_rules.ME12,
        business_rules.ME17,
        business_rules.ME24,
        business_rules.ME87,
        business_rules.ME33,
        business_rules.ME34,
        business_rules.ME40,
        business_rules.ME45,
        business_rules.ME46,
        business_rules.ME47,
        business_rules.ME109,
        business_rules.ME110,
        business_rules.ME111,
        business_rules.ME104,
    )

    objects = PolymorphicManager.from_queryset(MeasuresQuerySet)()

    @property
    def effective_end_date(self):
        """Measure end dates may be overridden by regulations"""

        # UK measures will have explicit end dates only
        # if self.national:
        #     return self.valid_between.upper

        reg = self.generating_regulation
        effective_end_date = (
            datetime(
                reg.effective_end_date.year,
                reg.effective_end_date.month,
                reg.effective_end_date.day,
                tzinfo=timezone.utc,
            )
            if reg.effective_end_date
            else None
        )

        if self.valid_between.upper and reg and effective_end_date:
            if self.valid_between.upper > effective_end_date:
                return effective_end_date
            return self.valid_between.upper

        if self.valid_between.upper and self.terminating_regulation:
            return self.valid_between.upper

        if reg:
            return effective_end_date

        return self.valid_between.upper

    @property
    def effective_valid_between(self):
        return TaricDateTimeRange(self.valid_between.lower, self.effective_end_date)

    def has_components(self):
        return (
            MeasureComponent.objects.approved_or_in_transaction(
                transaction=self.transaction
            )
            .filter(component_measure__sid=self.sid)
            .exists()
        )

    def has_condition_components(self):
        return (
            MeasureConditionComponent.objects.approved_or_in_transaction(
                transaction=self.transaction
            )
            .filter(condition__dependent_measure__sid=self.sid)
            .exists()
        )


class MeasureComponent(TrackedModel):
    """Contains the duty information or part of the duty information."""

    record_code = "430"
    subrecord_code = "05"

    component_measure = models.ForeignKey(
        Measure, on_delete=models.PROTECT, related_name="components"
    )
    duty_expression = models.ForeignKey(DutyExpression, on_delete=models.PROTECT)
    duty_amount = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True
    )
    monetary_unit = models.ForeignKey(
        MonetaryUnit, on_delete=models.PROTECT, null=True, blank=True
    )
    component_measurement = models.ForeignKey(
        Measurement, on_delete=models.PROTECT, null=True, blank=True
    )

    identifying_fields = ("component_measure__sid", "duty_expression__sid")

    business_rules = (
        business_rules.ME41,
        business_rules.ME42,
        business_rules.ME43,
        business_rules.ME48,
        business_rules.ME49,
        business_rules.ME50,
        business_rules.ME51,
        business_rules.ME52,
    )


class MeasureCondition(TrackedModel):
    """A measure may be dependent on conditions. These are expressed in a series of
    conditions, each having zero or more components. Conditions for the same condition
    type will have sequence numbers. Conditions of different types may be combined.
    """

    record_code = "430"
    subrecord_code = "10"

    sid = SignedIntSID(db_index=True)
    dependent_measure = models.ForeignKey(
        Measure, on_delete=models.PROTECT, related_name="conditions"
    )
    condition_code = models.ForeignKey(
        MeasureConditionCode, on_delete=models.PROTECT, related_name="conditions"
    )
    component_sequence_number = models.PositiveSmallIntegerField(
        validators=[validators.validate_component_sequence_number]
    )
    duty_amount = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True
    )
    monetary_unit = models.ForeignKey(
        MonetaryUnit, on_delete=models.PROTECT, null=True, blank=True
    )
    condition_measurement = models.ForeignKey(
        Measurement, on_delete=models.PROTECT, null=True, blank=True
    )
    action = models.ForeignKey(
        MeasureAction, on_delete=models.PROTECT, null=True, blank=True
    )
    required_certificate = models.ForeignKey(
        "certificates.Certificate", on_delete=models.PROTECT, null=True, blank=True
    )

    business_rules = (
        business_rules.MC3,
        business_rules.MA4,
        business_rules.ME56,
        business_rules.ME57,
        business_rules.ME58,
        business_rules.ME59,
        business_rules.ME60,
        business_rules.ME61,
        business_rules.ME62,
        business_rules.ME63,
        business_rules.ME64,
    )


class MeasureConditionComponent(TrackedModel):
    """Contains the duty information or part of the duty information of the measure
    condition.
    """

    record_code = "430"
    subrecord_code = "11"

    condition = models.ForeignKey(
        MeasureCondition, on_delete=models.PROTECT, related_name="components"
    )
    duty_expression = models.ForeignKey("DutyExpression", on_delete=models.PROTECT)
    duty_amount = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True
    )
    monetary_unit = models.ForeignKey(
        MonetaryUnit, on_delete=models.PROTECT, null=True, blank=True
    )
    condition_component_measurement = models.ForeignKey(
        Measurement, on_delete=models.PROTECT, null=True, blank=True
    )

    identifying_fields = ("condition__sid", "duty_expression__sid")

    business_rules = (
        business_rules.ME53,
        business_rules.ME105,
        business_rules.ME106,
        business_rules.ME108,
    )


class MeasureExcludedGeographicalArea(TrackedModel):
    """The measure excluded geographical area modifies the applicable geographical area
    of a measure, which must be a geographical area group.
    """

    record_code = "430"
    subrecord_code = "15"

    identifying_fields = ("modified_measure__sid", "excluded_geographical_area__sid")

    modified_measure = models.ForeignKey(
        Measure, on_delete=models.PROTECT, related_name="exclusions"
    )
    excluded_geographical_area = models.ForeignKey(
        "geo_areas.GeographicalArea", on_delete=models.PROTECT
    )

    business_rules = (
        business_rules.ME65,
        business_rules.ME66,
        business_rules.ME67,
        business_rules.ME68,
    )


class FootnoteAssociationMeasure(TrackedModel):
    """The association of a footnote and a measure is always applicable for the entire
    period of the measure.
    """

    record_code = "430"
    subrecord_code = "20"

    footnoted_measure = models.ForeignKey(Measure, on_delete=models.PROTECT)
    associated_footnote = models.ForeignKey(
        "footnotes.Footnote", on_delete=models.PROTECT
    )

    identifying_fields = (
        "footnoted_measure__sid",
        "associated_footnote__footnote_id",
        "associated_footnote__footnote_type__footnote_type_id",
    )

    business_rules = (
        business_rules.ME69,
        business_rules.ME70,
        business_rules.ME71,
        business_rules.ME73,
    )
