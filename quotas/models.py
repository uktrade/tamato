from decimal import Decimal
from typing import Optional

from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.urls import NoReverseMatch
from django.urls import reverse
from polymorphic.managers import PolymorphicManager

from common import validators
from common.business_rules import UniqueIdentifyingFields
from common.business_rules import UpdateValidity
from common.fields import ShortDescription
from common.fields import SignedIntSID
from common.models import TrackedModel
from common.models.managers import TrackedModelManager
from common.models.mixins.validity import ValidityMixin
from common.models.utils import GetTabURLMixin
from common.validators import UpdateType
from quotas import business_rules
from quotas import querysets
from quotas import validators
from workbaskets.validators import WorkflowStatus


class QuotaOrderNumber(TrackedModel, ValidityMixin):
    """
    The order number is the identification of a quota.

    It is defined for tariff quotas and surveillances. If an operator wants to
    benefit from a tariff quota, they must refer to it via the order number in
    the customs declaration. An order number may have multiple associated quota
    definitions, for example to divide a quota over several time periods.
    """

    record_code = "360"
    subrecord_code = "00"

    identifying_fields = ("sid",)

    sid = SignedIntSID(db_index=True)
    order_number = models.CharField(
        max_length=6,
        validators=[validators.quota_order_number_validator],
        db_index=True,
    )
    mechanism = models.PositiveSmallIntegerField(
        choices=validators.AdministrationMechanism.choices,
    )
    category = models.PositiveSmallIntegerField(
        choices=validators.QuotaCategory.choices,
    )

    origins = models.ManyToManyField(
        "geo_areas.GeographicalArea",
        through="QuotaOrderNumberOrigin",
        related_name="quotas",
    )

    required_certificates = models.ManyToManyField(
        "certificates.Certificate",
        related_name="quotas",
    )

    indirect_business_rules = (
        business_rules.ON7,
        business_rules.ON8,
        business_rules.QBP2,
        business_rules.QD1,
        business_rules.QD7,
        business_rules.CertificateValidityPeriodMustSpanQuotaOrderNumber,
        business_rules.CertificatesMustExist,
    )
    business_rules = (
        business_rules.ON1,
        business_rules.ON2,
        business_rules.ON4,
        business_rules.ON9,
        business_rules.ON11,
        UniqueIdentifyingFields,
        UpdateValidity,
    )

    objects = TrackedModelManager.from_queryset(querysets.QuotaOrderNumberQuerySet)()

    def __str__(self):
        return self.order_number

    @property
    def autocomplete_label(self):
        return f"{self} ({self.valid_between.lower} - {self.valid_between.upper})"

    @property
    def is_origin_quota(self):
        return any(self.required_certificates.all())

    @property
    def geographical_exclusion_descriptions(self):
        origin_ids = list(
            self.quotaordernumberorigin_set.latest_approved().values_list(
                "pk",
                flat=True,
            ),
        )
        exclusions = QuotaOrderNumberOriginExclusion.objects.latest_approved().filter(
            origin_id__in=origin_ids,
        )
        descriptions = [
            exclusion.excluded_geographical_area.get_description().description
            for exclusion in exclusions
        ]

        return sorted(descriptions)

    class Meta:
        verbose_name = "quota"


class QuotaOrderNumberOrigin(TrackedModel, ValidityMixin):
    """The order number origin defines a quota as being available only to
    imports from a specific origin, usually a country or group of countries."""

    record_code = "360"
    subrecord_code = "10"
    identifying_fields = ("sid",)
    url_pattern_name_prefix = "quota"
    url_suffix = ""
    url_relation_field = "order_number"

    objects = PolymorphicManager.from_queryset(
        querysets.QuotaOrderNumberOriginQuerySet,
    )()

    sid = SignedIntSID(db_index=True)
    order_number = models.ForeignKey(QuotaOrderNumber, on_delete=models.PROTECT)
    geographical_area = models.ForeignKey(
        "geo_areas.GeographicalArea",
        on_delete=models.PROTECT,
    )

    excluded_areas = models.ManyToManyField(
        "geo_areas.GeographicalArea",
        through="QuotaOrderNumberOriginExclusion",
        related_name="+",
    )

    indirect_business_rules = (
        business_rules.ON13,
        business_rules.ON14,
    )
    business_rules = (
        business_rules.ON5,
        business_rules.ON6,
        business_rules.ON7,
        business_rules.ON10,
        business_rules.ON12,
        UniqueIdentifyingFields,
        UpdateValidity,
    )

    def order_number_in_use(self, transaction):
        return self.order_number.in_use(transaction)

    @property
    def structure_description(self):
        return (
            f"{self.geographical_area.get_area_code_display()} - "
            f"{self.geographical_area.structure_description} ({self.geographical_area.area_id})"
        )

    def get_url(self, action: str = "detail") -> Optional[str]:
        """
        Generate a URL to a representation of the model in the webapp.

        Callers should handle the case where no URL is returned.

        :param action str: The view type to generate a URL for (default
            "detail"), eg: "list" or "edit" :rtype Optional[str]: The generated
            URL
        """
        kwargs = {}
        if action not in ["list", "create"]:
            kwargs = self.get_identifying_fields()
        try:
            if (
                action == "edit"
                and self.transaction.workbasket.status == WorkflowStatus.EDITING
            ):
                # Edits in WorkBaskets that are in EDITING state get real
                # changes via DB updates, not newly created UPDATE instances.
                if self.update_type == UpdateType.CREATE:
                    action += "-create"
                elif self.update_type == UpdateType.UPDATE:
                    action += "-update"

            if action == "detail":
                url = reverse(
                    f"{self.get_url_pattern_name_prefix()}-ui-{action}",
                    kwargs={"sid": getattr(self, self.url_relation_field).sid},
                )
            else:
                url = reverse(
                    f"{self.slugify_model_name()}-ui-{action}",
                    kwargs=kwargs,
                )
            return f"{url}{self.url_suffix}"
        except NoReverseMatch:
            return None

    @classmethod
    def slugify_model_name(cls):
        return cls._meta.verbose_name.replace(" ", "_")


class QuotaOrderNumberOriginExclusion(GetTabURLMixin, TrackedModel):
    """Origin exclusions specify countries (or groups of countries, or other
    origins) to exclude from the quota number origin."""

    url_pattern_name_prefix = "geo_area"
    url_suffix = ""
    url_relation_field = "excluded_geographical_area"

    record_code = "360"
    subrecord_code = "15"

    objects = PolymorphicManager.from_queryset(
        querysets.QuotaOrderNumberOriginExclusionQuerySet,
    )()

    origin = models.ForeignKey(QuotaOrderNumberOrigin, on_delete=models.PROTECT)
    excluded_geographical_area = models.ForeignKey(
        "geo_areas.GeographicalArea",
        on_delete=models.PROTECT,
    )

    identifying_fields = "origin__sid", "excluded_geographical_area__sid"

    business_rules = (
        business_rules.ON13,
        business_rules.ON14,
        UpdateValidity,
    )

    @property
    def structure_description(self):
        return (
            f"{self.excluded_geographical_area.get_area_code_display()} - "
            f"{self.excluded_geographical_area.structure_description} ({self.excluded_geographical_area.area_id})"
        )


class QuotaDefinition(TrackedModel, ValidityMixin):
    """
    Defines the validity period and quantity for which a quota is applicable.
    This model also represents sub-quotas, via a parent-child recursive relation
    through QuotaAssociation.

    The monetary unit code and the measurement unit code (with its optional unit
    qualifier code) are mutually exclusive – each quota definition must have one
    and only one of monetary or measurement unit.

    The pair of measurement and measurement unit qualifier must appear as a
    valid measurement in the measurements table.
    """

    record_code = "370"
    subrecord_code = "00"

    identifying_fields = ("sid",)

    url_pattern_name_prefix = "quota"
    url_suffix = "#definition-details"
    url_relation_field = "order_number"

    sid = SignedIntSID(db_index=True)
    order_number = models.ForeignKey(
        QuotaOrderNumber,
        on_delete=models.PROTECT,
        related_name="definitions",
    )
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
        validators=[validators.validate_max_precision],
    )
    quota_critical = models.BooleanField(default=False)
    # the percentage at which the quota becomes critical
    quota_critical_threshold = models.PositiveSmallIntegerField(
        validators=[validators.validate_percentage],
    )
    description = ShortDescription()

    sub_quotas = models.ManyToManyField(
        "self",
        through="QuotaAssociation",
        through_fields=("main_quota", "sub_quota"),
    )

    indirect_business_rules = (
        business_rules.QA2,
        business_rules.QA3,
        business_rules.QA5,
        business_rules.QSP2,
    )
    business_rules = (
        business_rules.ON8,
        business_rules.QD1,
        business_rules.QD7,
        business_rules.QD8,
        business_rules.QD10,
        business_rules.QD11,
        business_rules.PreventQuotaDefinitionDeletion,
        business_rules.QuotaAssociationMustReferToANonDeletedSubQuota,
        business_rules.QuotaSuspensionMustReferToANonDeletedQuotaDefinition,
        business_rules.QuotaBlockingPeriodMustReferToANonDeletedQuotaDefinition,
        business_rules.OverlappingQuotaDefinition,
        business_rules.VolumeAndInitialVolumeMustMatch,
        UniqueIdentifyingFields,
        UpdateValidity,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(
                        monetary_unit__isnull=False,
                        measurement_unit__isnull=True,
                    )
                    | models.Q(
                        monetary_unit__isnull=True,
                        measurement_unit__isnull=False,
                    )
                ),
                name="quota_definition_must_have_one_unit",
            ),
        ]

    def __str__(self):
        return str(self.sid)

    def get_url(self, action: str = "detail") -> Optional[str]:
        """
        Generate a URL to a representation of the model in the webapp.

        Callers should handle the case where no URL is returned.

        :param action str: The view type to generate a URL for (default
            "detail"), eg: "list" or "edit" :rtype Optional[str]: The generated
            URL
        """
        kwargs = self.get_identifying_fields()
        if (
            action == "edit"
            and self.transaction.workbasket.status == WorkflowStatus.EDITING
        ):
            # Edits in WorkBaskets that are in EDITING state get real
            # changes via DB updates, not newly created UPDATE instances.
            if self.update_type == UpdateType.CREATE:
                action += "-create"
            elif self.update_type == UpdateType.UPDATE:
                action += "-update"

        if action == "detail":
            url = reverse(
                f"{self.get_url_pattern_name_prefix()}-ui-{action}",
                kwargs={"sid": getattr(self, self.url_relation_field).sid},
            )
            return f"{url}{self.url_suffix}"

        if action in ["create", "list"]:
            url = reverse(
                f"{self.slugify_model_name()}-ui-{action}",
                kwargs={"sid": getattr(self, self.url_relation_field).sid},
            )
        else:
            url = reverse(f"{self.slugify_model_name()}-ui-{action}", kwargs=kwargs)
        return url

    @classmethod
    def slugify_model_name(cls):
        return cls._meta.verbose_name.replace(" ", "_")


class QuotaAssociation(TrackedModel):
    """The quota association defines the relation between quota and sub-
    quotas."""

    record_code = "370"
    subrecord_code = "05"

    main_quota = models.ForeignKey(
        QuotaDefinition,
        on_delete=models.PROTECT,
        related_name="sub_quota_associations",
    )
    sub_quota = models.ForeignKey(
        QuotaDefinition,
        on_delete=models.PROTECT,
        related_name="main_quota_associations",
    )
    sub_quota_relation_type = models.CharField(
        max_length=2,
        choices=validators.SubQuotaType.choices,
    )
    coefficient = models.DecimalField(
        max_digits=16,
        decimal_places=5,
        default=Decimal("1.00000"),
        validators=[validators.validate_coefficient],
    )
    identifying_fields = ("main_quota__sid", "sub_quota__sid")

    business_rules = (
        business_rules.QA1,
        business_rules.QA2,
        business_rules.QA3,
        business_rules.QA4,
        business_rules.QA5,
        business_rules.QA6,
        UpdateValidity,
        business_rules.SameMainAndSubQuota,
    )


class QuotaSuspension(TrackedModel, ValidityMixin):
    """Defines a suspension period for a quota."""

    record_code = "370"
    subrecord_code = "15"

    identifying_fields = ("sid",)

    sid = SignedIntSID(db_index=True)
    quota_definition = models.ForeignKey(QuotaDefinition, on_delete=models.PROTECT)
    description = ShortDescription()

    business_rules = (business_rules.QSP2, UniqueIdentifyingFields, UpdateValidity)


class QuotaBlocking(TrackedModel, ValidityMixin):
    """Defines a blocking period for a (sub-)quota."""

    record_code = "370"
    subrecord_code = "10"

    identifying_fields = ("sid",)

    sid = SignedIntSID(db_index=True)
    quota_definition = models.ForeignKey(QuotaDefinition, on_delete=models.PROTECT)
    blocking_period_type = models.PositiveSmallIntegerField(
        choices=validators.BlockingPeriodType.choices,
    )
    description = ShortDescription()

    business_rules = (business_rules.QBP2, UniqueIdentifyingFields, UpdateValidity)


class QuotaEvent(TrackedModel):
    """
    We do not care about quota events, except to store historical data.

    So this model stores all events in a single table.
    """

    record_code = "375"
    subrecord_code = models.CharField(
        max_length=2,
        choices=validators.QuotaEventType.choices,
        db_index=True,
    )
    quota_definition = models.ForeignKey(QuotaDefinition, on_delete=models.PROTECT)
    occurrence_timestamp = models.DateTimeField()
    # store the event-type specific data in a JSON object
    data = models.JSONField(default=dict, encoder=DjangoJSONEncoder)

    identifying_fields = ("subrecord_code", "quota_definition__sid")

    business_rules = (UpdateValidity,)
