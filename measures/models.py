import json
import logging
from datetime import date
from typing import Iterable
from typing import Set

from django.core.exceptions import ValidationError
from django.db import models
from django.db.transaction import atomic
from django.forms.formsets import BaseFormSet

from common.business_rules import UniqueIdentifyingFields
from common.business_rules import UpdateValidity
from common.fields import ApplicabilityCode
from common.fields import ShortDescription
from common.fields import SignedIntSID
from common.models import TrackedModel
from common.models.managers import TrackedModelManager
from common.models.mixins.validity import ValidityMixin
from common.models.utils import GetTabURLMixin
from common.models.utils import set_current_transaction
from common.util import TaricDateRange
from common.util import classproperty
from footnotes import validators as footnote_validators
from measures import business_rules
from measures import validators
from measures.querysets import ComponentQuerySet
from measures.querysets import MeasureConditionQuerySet
from measures.querysets import MeasuresQuerySet
from quotas import business_rules as quotas_business_rules
from quotas.validators import quota_order_number_validator

logger = logging.getLogger(__name__)


class MeasureTypeSeries(TrackedModel, ValidityMixin):
    """
    Measure types may be grouped into series.

    The series can be used to determine how duties are applied, and the possible
    cumulative effect of other applicable measures.
    """

    record_code = "140"
    subrecord_code = "00"

    description_record_code = "140"
    description_subrecord_code = "05"

    identifying_fields = ("sid",)

    sid = models.CharField(
        max_length=2,
        validators=[validators.measure_type_series_id_validator],
        db_index=True,
    )
    measure_type_combination = models.PositiveSmallIntegerField(
        choices=validators.MeasureTypeCombination.choices,
    )
    description = ShortDescription()

    indirect_business_rules = (business_rules.MT10,)
    business_rules = (
        business_rules.MTS1,
        business_rules.MTS2,
        UpdateValidity,
    )


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

    indirect_business_rules = (
        business_rules.ME51,
        business_rules.ME63,
    )

    business_rules = (UpdateValidity,)


class MeasurementUnitQualifier(TrackedModel, ValidityMixin):
    """
    The measurement unit qualifier is used to qualify a measurement unit.

    For example the measurement unit "kilogram" may be qualified as "net" or
    "gross".
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

    indirect_business_rules = (
        business_rules.ME52,
        business_rules.ME64,
        quotas_business_rules.QD11,
    )

    business_rules = (UpdateValidity,)


class Measurement(TrackedModel, ValidityMixin):
    """
    The measurement defines the relationship between a measurement unit and a
    measurement unit qualifier.

    This avoids meaningless combinations of the measurement unit and the
    measurement unit qualifier. Unlike in the TARIC model, we put all
    combinations of measurement in this table including ones where the qualifier
    is null. These do not appear in output XML.
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

    indirect_business_rules = (
        business_rules.ME50,
        business_rules.ME62,
    )

    business_rules = (UpdateValidity,)


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

    indirect_business_rules = (
        business_rules.ME48,
        business_rules.ME49,
        business_rules.ME60,
        business_rules.ME61,
        quotas_business_rules.QD8,
    )

    business_rules = (UpdateValidity,)


class DutyExpression(TrackedModel, ValidityMixin):
    """
    The duty expression identifies the type of duty which must be applied for a
    given measure component.

    It will also control how the duty will be expressed, for example whether an
    amount is "permitted" or "mandatory".
    """

    record_code = "230"
    subrecord_code = "00"

    description_record_code = "230"
    description_subrecord_code = "05"

    identifying_fields = ("sid",)

    sid = models.IntegerField(
        choices=validators.DutyExpressionId.choices,
        db_index=True,
    )
    prefix = models.CharField(max_length=14, blank=True)
    duty_amount_applicability_code = ApplicabilityCode()
    measurement_unit_applicability_code = ApplicabilityCode()
    monetary_unit_applicability_code = ApplicabilityCode()
    description = ShortDescription()

    indirect_business_rules = (
        business_rules.ME40,
        business_rules.ME42,
        business_rules.ME45,
        business_rules.ME46,
        business_rules.ME47,
        business_rules.ME105,
        business_rules.ME106,
        business_rules.ME109,
        business_rules.ME110,
        business_rules.ME111,
    )

    business_rules = (UniqueIdentifyingFields, UpdateValidity)


class MeasureType(TrackedModel, ValidityMixin):
    """
    The measure type identifies a customs measure.

    TARIC customs measures cover a wide range of information, including tariff
    measures (such as levies and anti-dumping duties), and non-tariff measures
    (such as quantitative restrictions and prohibitions).
    """

    record_code = "235"
    subrecord_code = "00"

    description_record_code = "235"
    description_subrecord_code = "05"

    identifying_fields = ("sid",)

    sid = models.CharField(
        max_length=6,
        validators=[validators.measure_type_id_validator],
        db_index=True,
    )
    trade_movement_code = models.PositiveSmallIntegerField(
        choices=validators.ImportExportCode.choices,
    )
    priority_code = models.PositiveSmallIntegerField(
        validators=[validators.validate_priority_code],
    )
    measure_component_applicability_code = ApplicabilityCode()
    origin_destination_code = models.PositiveSmallIntegerField(
        choices=validators.ImportExportCode.choices,
    )
    order_number_capture_code = models.PositiveSmallIntegerField(
        choices=validators.OrderNumberCaptureCode.choices,
    )
    measure_explosion_level = models.PositiveSmallIntegerField(
        choices=validators.MeasureExplosionLevel.choices,
        validators=[validators.validate_measure_explosion_level],
    )
    description = ShortDescription()
    measure_type_series = models.ForeignKey(MeasureTypeSeries, on_delete=models.PROTECT)

    additional_code_types = models.ManyToManyField(
        "additional_codes.AdditionalCodeType",
        through="AdditionalCodeTypeMeasureType",
    )

    indirect_business_rules = (
        business_rules.ME1,
        business_rules.ME10,
        business_rules.ME88,
    )
    business_rules = (
        business_rules.MT1,
        business_rules.MT3,
        business_rules.MT4,
        business_rules.MT7,
        business_rules.MT10,
        UpdateValidity,
    )

    def __str__(self):
        return str(self.sid)

    @property
    def autocomplete_label(self):
        return f"{self} - {self.description}"

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
    coherent association between additional codes and measures."""

    record_code = "240"
    subrecord_code = "00"

    measure_type = models.ForeignKey(MeasureType, on_delete=models.PROTECT)
    additional_code_type = models.ForeignKey(
        "additional_codes.AdditionalCodeType",
        on_delete=models.PROTECT,
    )

    identifying_fields = ("measure_type", "additional_code_type")

    business_rules = (UpdateValidity,)


class MeasureConditionCode(TrackedModel, ValidityMixin):
    """A measure condition code identifies a broad area where conditions are
    required, for example "C" will have the description "required to present a
    certificate"."""

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
    # A measure condition code must be created with one or both of
    # accepts_certificate and accepts_price set to True,
    # though a condition should only ever have one of either required_certificate or duty_amount set.
    accepts_certificate = models.BooleanField(default=False)
    accepts_price = models.BooleanField(default=False)

    identifying_fields = ("code",)

    business_rules = (
        business_rules.MC1,
        business_rules.MC4,
        UpdateValidity,
    )

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.description}"

    def __lt__(self, other):
        """Can sort MeasureConditionCode by their alphabetical code."""
        return self.code < other.code


class MeasureAction(TrackedModel, ValidityMixin):
    """
    The measure action identifies the action to take when a given condition is
    met.

    For example, the description of "01" will be "apply ACTION AMOUNT".
    """

    record_code = "355"
    subrecord_code = "00"

    description_record_code = "355"
    description_subrecord_code = "05"

    code = models.CharField(
        max_length=3,
        validators=[validators.validate_action_code],
        db_index=True,
    )
    description = ShortDescription()
    requires_duty = models.BooleanField(default=False)

    identifying_fields = ("code",)

    indirect_business_rules = (
        business_rules.MA4,
        business_rules.ME59,
    )
    business_rules = (
        business_rules.MA1,
        business_rules.MA2,
        UpdateValidity,
    )

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.description}"


class MeasureActionPair(models.Model):
    """
    Defines the positive and negative linkage between two MeasureActions Not all
    MeasureActions will have a pair when querying on measure action do a left
    join.

    query - values list on negative action and exclude from MeasureAction
    """

    positive_action = models.ForeignKey(
        MeasureAction,
        on_delete=models.PROTECT,
        editable=False,
        related_name="positive_measure_action",
        unique=True,
    )
    negative_action = models.ForeignKey(
        MeasureAction,
        on_delete=models.PROTECT,
        editable=False,
        related_name="negative_measure_action",
        unique=True,
    )

    class Meta:
        ordering = ["pk"]

    def save(self, *args, **kwargs):
        """Throws a validation error if the positive and negative action are
        equal Throws a validation error if the positive action has already been
        created as a negative action Throws a validation error if the negative
        action has already been created as a positive action."""
        positive_action = getattr(self, "positive_action")
        negative_action = getattr(self, "negative_action")

        if positive_action == negative_action:
            raise ValidationError("Positive and negative action cannot be equal.")
        elif MeasureActionPair.objects.filter(negative_action=positive_action).exists():
            raise ValidationError(
                "Cannot create positive action as it is already a negative action.",
            )
        elif MeasureActionPair.objects.filter(positive_action=negative_action).exists():
            raise ValidationError(
                "Cannot create negative action as it is already a positive action.",
            )

        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Positive Action: {self.positive_action.code} - Negative Action: {self.negative_action.code}"


class Measure(TrackedModel, ValidityMixin):
    """
    Defines the validity period in which a particular measure type is applicable
    to particular nomenclature for a particular geographical area.

    Measures in the TARIC database are stored against the nomenclature code
    which is at the highest level appropriate in the hierarchy. Thus, measures
    which apply to all the declarable codes in a complete chapter are stored
    against the nomenclature code for the chapter (i.e. at the 2-digit level
    only); those which apply to all sub-divisions of an HS code are stored
    against that HS code (i.e. at the 6-digit level only). The advantage of this
    system is that it reduces the number of measures stored in the database; the
    data capture workload (thus diminishing the possibility of introducing
    errors) and the transmission volumes.
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
        max_length=16,
        null=True,
        blank=True,
        db_index=True,
    )
    order_number = models.ForeignKey(
        "quotas.QuotaOrderNumber",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
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
        "regulations.Regulation",
        on_delete=models.PROTECT,
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
        "footnotes.Footnote",
        through="FootnoteAssociationMeasure",
    )

    identifying_fields = ("sid",)

    indirect_business_rules = (
        business_rules.MA4,
        business_rules.MC3,
        business_rules.ME42,
        business_rules.ME49,
        business_rules.ME61,
        business_rules.ME65,
        business_rules.ME66,
        business_rules.ME67,
        business_rules.ME71,
        business_rules.ME73,
    )
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
        business_rules.ME27,
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
        UniqueIdentifyingFields,
        UpdateValidity,
    )

    objects = TrackedModelManager.from_queryset(MeasuresQuerySet)()

    @property
    def footnote_application_codes(self) -> Set[footnote_validators.ApplicationCode]:
        codes = {footnote_validators.ApplicationCode.DYNAMIC_FOOTNOTE}
        if self.goods_nomenclature:
            codes.add(footnote_validators.ApplicationCode.OTHER_MEASURES)
        if not self.goods_nomenclature.is_taric_code:
            codes.add(footnote_validators.ApplicationCode.CN_MEASURES)
        return codes

    validity_field_name = "db_effective_valid_between"

    @property
    def effective_end_date(self) -> date:
        """Measure end dates may be overridden by regulations."""
        if not hasattr(self, self.validity_field_name):
            effective_valid_between = (
                type(self)
                .objects.with_validity_field()
                .filter(pk=self.pk)
                .get()
                .db_effective_valid_between
            )
            setattr(self, self.validity_field_name, effective_valid_between)

        return getattr(self, self.validity_field_name).upper

    def __str__(self):
        return str(self.sid)

    @property
    def effective_valid_between(self) -> TaricDateRange:
        if hasattr(self, self.validity_field_name):
            return getattr(self, self.validity_field_name)

        return TaricDateRange(self.valid_between.lower, self.effective_end_date)

    @property
    def duty_sentence(self) -> str:
        return MeasureComponent.objects.duty_sentence(self)

    @classproperty
    def auto_value_fields(cls):
        """Remove export refund SID because we don't want to auto-increment it –
        it should really be a foreign key to an ExportRefundNomenclature model
        but as we don't use them in the UK Tariff we don't store them."""
        counters = super().auto_value_fields
        counters.remove(cls._meta.get_field("export_refund_nomenclature_sid"))
        return counters

    def has_components(self, transaction):
        return (
            MeasureComponent.objects.approved_up_to_transaction(transaction)
            .filter(component_measure__sid=self.sid)
            .exists()
        )

    def has_condition_components(self, transaction):
        return (
            MeasureConditionComponent.objects.approved_up_to_transaction(transaction)
            .filter(condition__dependent_measure__sid=self.sid)
            .exists()
        )


class MeasureComponent(TrackedModel):
    """Contains the duty information or part of the duty information."""

    record_code = "430"
    subrecord_code = "05"

    component_measure = models.ForeignKey(
        Measure,
        on_delete=models.PROTECT,
        related_name="components",
    )
    duty_expression = models.ForeignKey(DutyExpression, on_delete=models.PROTECT)
    duty_amount = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
    )
    monetary_unit = models.ForeignKey(
        MonetaryUnit,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    component_measurement = models.ForeignKey(
        Measurement,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    identifying_fields = ("component_measure__sid", "duty_expression__sid")

    indirect_business_rules = (
        business_rules.ME40,
        business_rules.ME45,
        business_rules.ME46,
        business_rules.ME47,
    )
    business_rules = (
        business_rules.ME41,
        business_rules.ME42,
        business_rules.ME43,
        business_rules.ME48,
        business_rules.ME49,
        business_rules.ME50,
        business_rules.ME51,
        business_rules.ME52,
        UpdateValidity,
    )

    objects = TrackedModelManager.from_queryset(ComponentQuerySet)()


class MeasureCondition(GetTabURLMixin, TrackedModel):
    """
    A measure may be dependent on conditions.

    These are expressed in a series of conditions, each having zero or more
    components. Conditions for the same condition type will have sequence
    numbers. Conditions of different types may be combined.
    """

    record_code = "430"
    subrecord_code = "10"
    url_pattern_name_prefix = "measure"
    url_suffix = "#conditions"
    url_relation_field = "dependent_measure"

    identifying_fields = ("sid",)

    sid = SignedIntSID(db_index=True)
    dependent_measure = models.ForeignKey(
        Measure,
        on_delete=models.PROTECT,
        related_name="conditions",
    )
    condition_code = models.ForeignKey(
        MeasureConditionCode,
        on_delete=models.PROTECT,
        related_name="conditions",
    )
    component_sequence_number = models.PositiveSmallIntegerField(
        validators=[validators.validate_component_sequence_number],
    )
    duty_amount = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
    )
    monetary_unit = models.ForeignKey(
        MonetaryUnit,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    condition_measurement = models.ForeignKey(
        Measurement,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    action = models.ForeignKey(
        MeasureAction,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    required_certificate = models.ForeignKey(
        "certificates.Certificate",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    objects = TrackedModelManager.from_queryset(MeasureConditionQuerySet)()

    indirect_business_rules = (
        business_rules.MA2,
        business_rules.MC4,
        business_rules.ME53,
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
        business_rules.ActionRequiresDuty,
        business_rules.ConditionCodeAcceptance,
        UniqueIdentifyingFields,
        UpdateValidity,
    )

    class Meta:
        ordering = [
            "dependent_measure__sid",
            "condition_code__code",
            "component_sequence_number",
        ]

    def is_certificate_required(self):
        return self.condition_code.code in ("A", "B", "C", "H", "Q", "Y", "Z")

    @property
    def description(self) -> str:
        out: list[str] = []

        out.append(
            f"Condition of type {self.condition_code.code} - {self.condition_code.description}",
        )

        if self.required_certificate:
            out.append(
                f"On presentation of certificate {self.required_certificate.code},",
            )
        elif self.is_certificate_required():
            out.append("On presentation of no certificate,")

        if hasattr(self, "reference_price_string") and self.reference_price_string:
            out.append(f"If reference price > {self.reference_price_string},")

        out.append(f"perform action {self.action.code} - {self.action.description}")

        if self.duty_sentence:
            out.append(f"\n\nApplicable duty is {self.duty_sentence}")

        return " ".join(out)

    @property
    def duty_sentence(self) -> str:
        return MeasureConditionComponent.objects.duty_sentence(self)


class MeasureConditionComponent(TrackedModel):
    """Contains the duty information or part of the duty information of the
    measure condition."""

    record_code = "430"
    subrecord_code = "11"

    condition = models.ForeignKey(
        MeasureCondition,
        on_delete=models.PROTECT,
        related_name="components",
    )
    duty_expression = models.ForeignKey("DutyExpression", on_delete=models.PROTECT)
    duty_amount = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
    )
    monetary_unit = models.ForeignKey(
        MonetaryUnit,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    component_measurement = models.ForeignKey(
        Measurement,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    identifying_fields = ("condition__sid", "duty_expression__sid")

    class Meta:
        ordering = [
            "condition__sid",
            "duty_expression__sid",
        ]

    indirect_business_rules = (
        business_rules.ME109,
        business_rules.ME110,
        business_rules.ME111,
        business_rules.ME40,
    )
    business_rules = (
        business_rules.ME53,
        business_rules.ME105,
        business_rules.ME106,
        business_rules.ME108,
        UpdateValidity,
    )

    objects = TrackedModelManager.from_queryset(ComponentQuerySet)()


class MeasureExcludedGeographicalArea(TrackedModel):
    """The measure excluded geographical area modifies the applicable
    geographical area of a measure, which must be a geographical area group."""

    record_code = "430"
    subrecord_code = "15"
    url_pattern_name_prefix = "geo_area"
    identifying_fields = ("modified_measure__sid", "excluded_geographical_area__sid")

    modified_measure = models.ForeignKey(
        Measure,
        on_delete=models.PROTECT,
        related_name="exclusions",
    )
    excluded_geographical_area = models.ForeignKey(
        "geo_areas.GeographicalArea",
        on_delete=models.PROTECT,
    )

    business_rules = (
        business_rules.ME65,
        business_rules.ME66,
        business_rules.ME67,
        business_rules.ME68,
        UpdateValidity,
    )

    def __str__(self):
        return (
            f"{self.excluded_geographical_area.get_area_code_display()} "
            f"{self.excluded_geographical_area.structure_description} {self.excluded_geographical_area.area_id}"
        )


class FootnoteAssociationMeasure(TrackedModel):
    """The association of a footnote and a measure is always applicable for the
    entire period of the measure."""

    record_code = "430"
    subrecord_code = "20"

    footnoted_measure = models.ForeignKey(Measure, on_delete=models.PROTECT)
    associated_footnote = models.ForeignKey(
        "footnotes.Footnote",
        on_delete=models.PROTECT,
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
        UpdateValidity,
    )


class MeasuresBulkCreator(models.Model):
    """
    Model class used to bulk create Measures instances from serialized form
    data.

    The stored form data is serialized and deserialized by Forms that subclass
    SerializableFormMixin.
    """

    form_data = models.JSONField()
    """Dictionary of all Form.data, used to reconstruct bound Form instances as
    if the form data had been sumbitted by the user within the measure wizard
    process."""

    form_kwargs = models.JSONField()
    """Dictionary of all form init data, excluding a form's `data` param (which
    is preserved via this class's `form_data` attribute)."""

    current_transaction = models.ForeignKey(
        "common.Transaction",
        on_delete=models.SET_NULL,
        null=True,
        related_name="measures_bulk_creators",
        editable=False,
    )
    """
    The 'current' Transaction instance at the time `form_data` was constructed.

    This is normally be set by
    `common.models.utils.TransactionMiddleware` when processing a HTTP request
    and can be obtained from `common.models.utils.get_current_transaction()`
    to capture its value.
    """

    # TODO:
    # - Is it preferable to save the Workbasket rather than the current
    #   transaction in the workbasket?
    #   The current transaction can change if more transactions are created
    #   before create_meassures() has chance to run. That could be good (we
    #   want objects at the time the user performed the create measures action)
    #   or bad (the current transaction may get deleted).
    #   However if workbasket immutability is guarenteed until create_measures()
    #   has completed, then this is moot. It'd need a 'protected' attribute, or
    #   something like that, on the WorkBasket class that freezes it, say, in
    #   the save() and update() methods.

    @atomic
    def create_measures(self) -> Iterable[Measure]:
        """Create measures using the instance's `cleaned_data`, returning the
        results as an iterable."""

        created_measures = []

        # Construction and / or validation of some Form instances require
        # access to a 'current' Transaction.
        set_current_transaction(self.current_transaction)

        logger.info(
            f"MeasuresBulkCreator.create_measures() - form_data:\n"
            f"{json.dumps(self.form_data, indent=4, default=str)}",
        )
        logger.info(
            f"MeasuresBulkCreator.create_measures() - form_kwargs:\n"
            f"{json.dumps(self.form_kwargs, indent=4, default=str)}",
        )

        # Avoid circular import.
        from measures.views import MeasureCreateWizard

        for form_key, form_class in MeasureCreateWizard.data_form_list:
            if form_key not in self.form_data:
                # Not all forms / steps are used to create measures. Some are
                # only conditionally included - see `MeasureCreateWizard.condition_dict`
                # and `MeasureCreateWizard.show_step()` for details.
                continue

            data = self.form_data[form_key]
            kwargs = form_class.deserialize_init_kwargs(self.form_kwargs[form_key])
            form = form_class(data=data, **kwargs)
            form = MeasureCreateWizard.fixup_form(form, self.current_transaction)
            is_valid = form.is_valid()

            logger.info(
                f"MeasuresBulkCreator.create_measures() - "
                f"{form_class.__name__}.is_valid(): {is_valid}",
            )
            if not is_valid:
                self._log_form_errors(form_class=form_class, form_or_formset=form)

        # TODO: Create the measures.

        return created_measures

    def _log_form_errors(self, form_class, form_or_formset) -> None:
        """Output errors associated with a Form or Formset instance, handling
        output for each instance type in a uniform manner."""

        logger.error(
            f"MeasuresBulkCreator.create_measures() - "
            f"{form_class.__name__} has {len(form_or_formset.errors)} unexpected "
            f"errors.",
        )

        # Form.errors is a dictionary of errors, but FormSet.errors is a
        # list of dictionaries of Form.errors. Access their errors in
        # a uniform manner.
        errors = []

        if isinstance(form_or_formset, BaseFormSet):
            errors = [
                {"formset_errors": form_or_formset.non_form_errors()},
            ] + form_or_formset.errors
        else:
            errors = [form_or_formset.errors]

        for form_errors in errors:
            for error_key, error_values in form_errors.items():
                logger.error(f"{error_key}: {error_values}")
