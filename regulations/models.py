from django.conf import settings
from django.core.validators import MaxValueValidator
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.fields import DateField

from common.business_rules import UpdateValidity
from common.fields import ShortDescription
from common.fields import TaricDateRangeField
from common.models import TrackedModel
from common.models.mixins.validity import ValidityMixin
from geo_areas.validators import area_id_validator
from measures.validators import measure_type_id_validator
from regulations import business_rules
from regulations import validators


class Group(TrackedModel, ValidityMixin):
    """
    A regulation group allows regulations to be grouped within the same logical
    unit. This allows the regulations covered by a certain regulation group to
    be identified. Consequently it is possible to identify the measure types
    and/or countries which relate to a regulation group. Only base regulations
    can be associated with a regulation group.

    Regulations can only belong to a single Regulation group.

    Regulations groups do not have end dates set.

    Regulation groups must not be modified.
    """

    record_code = "150"
    subrecord_code = "00"

    description_subrecord_code = "05"

    group_id = models.CharField(
        max_length=3,
        editable=False,
        validators=[RegexValidator(r"[A-Z][A-Z][A-Z]")],
        db_index=True,
    )
    description = ShortDescription()

    identifying_fields = ("group_id",)

    indirect_business_rules = (
        business_rules.ROIMB4,
        business_rules.ROIMB47,
    )

    business_rules = (UpdateValidity,)

    def __str__(self):
        return f"{self.group_id}: {self.description}"


class Regulation(TrackedModel):
    """
    The main legal acts at the basis of the Union tariff and commercial
    legislation are regulations and decisions.

    They can have one or several roles: base, provisional or definitive
    antidumping, modification, complete abrogation, explicit abrogation,
    prorogation (extension), Full Temporary Stop (FTS), Partial Temporary Stop
    (PTS)
    """

    identifying_fields = ("role_type", "regulation_id")

    record_code = "285"
    subrecord_code = "00"

    role_type = models.PositiveIntegerField(
        choices=validators.RoleType.choices,
        default=validators.RoleType.BASE,
        editable=False,
        db_index=True,
    )
    regulation_id = models.CharField(
        max_length=8,
        editable=False,
        validators=[validators.regulation_id_validator],
        help_text="The regulation number",
        db_index=True,
    )
    official_journal_number = models.CharField(
        max_length=5,
        null=True,
        blank=True,
        editable=False,
        default="1",
    )
    official_journal_page = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        validators=[MaxValueValidator(9999)],
        editable=False,
        default=1,
    )
    published_at = models.DateField(
        blank=True,
        null=True,
    )
    information_text = ShortDescription(
        validators=[validators.no_information_text_delimiters],
    )
    public_identifier = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="This is the name of the regulation as it would appear on (for example) legislation.gov.uk",
        validators=[validators.no_information_text_delimiters],
    )
    url = models.URLField(
        blank=True,
        null=True,
        help_text="Please enter the absolute URL of the regulation",
        validators=[validators.no_information_text_delimiters],
    )

    # Indicates if a (draft) regulation is approved.
    # Measures associated with an unapproved draft regulation are only for information and
    # do not apply.
    # If the draft regulation is rejected, all associated measures are deleted.
    # If approved, all measures apply.
    # Once the actual regulation is known, it replaces the draft regulation and all
    # measures are moved from the draft to the actual regulation.
    # It is possible for a draft regulation to be replaced by multiple actual regulations,
    # each one partially replacing the draft.
    approved = models.BooleanField(
        default=False,
        help_text=(
            "An unapproved status means none of the measures that link to "
            "this regulation will be active at the border."
        )
    )

    """The code which indicates whether or not a regulation has been replaced."""
    replacement_indicator = models.PositiveIntegerField(
        choices=validators.ReplacementIndicator.choices,
        default=validators.ReplacementIndicator.NOT_REPLACED,
        editable=False,
    )

    # Complete Abrogation, Explicit Abrogation and Prorogation regulations have no
    # validity period
    if settings.SQLITE:
        validity_start = DateField(db_index=True, null=True, blank=True)
        validity_end = DateField(db_index=True, null=True, blank=True)
    else:
        valid_between = TaricDateRangeField(blank=True, null=True)

    # Base, Modification and FTS regulations have an effective end date
    effective_end_date = models.DateField(blank=True, null=True, editable=False)

    # XXX do we need to store this? - i think it is already captured by
    #     self.terminations.count() > 0
    stopped = models.BooleanField(default=False)

    # Base regulations have community_code and regulation_group
    community_code = models.PositiveIntegerField(
        choices=validators.CommunityCode.choices,
        blank=True,
        null=True,
        default=validators.CommunityCode.ECONOMIC,
    )
    regulation_group = models.ForeignKey(
        Group,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )

    amends = models.ManyToManyField(
        "Regulation",
        through="Amendment",
        related_name="+",
        through_fields=("enacting_regulation", "target_regulation"),
    )

    extends = models.ManyToManyField(
        "Regulation",
        through="Extension",
        related_name="+",
        through_fields=("enacting_regulation", "target_regulation"),
    )

    suspends = models.ManyToManyField(
        "Regulation",
        through="Suspension",
        related_name="+",
        through_fields=("enacting_regulation", "target_regulation"),
    )

    terminates = models.ManyToManyField(
        "Regulation",
        through="Termination",
        related_name="+",
        through_fields=("enacting_regulation", "target_regulation"),
    )

    replaces = models.ManyToManyField(
        "Regulation",
        through="Replacement",
        related_name="+",
        through_fields=("enacting_regulation", "target_regulation"),
    )

    business_rules = (
        business_rules.ROIMB1,
        business_rules.ROIMB4,
        business_rules.ROIMB8,
        business_rules.ROIMB44,
        business_rules.ROIMB46,
        business_rules.ROIMB47,
        UpdateValidity,
    )

    @property
    def structure_description(self):
        return self.information_text

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        # store db values to detect changes
        instance.values_from_db = dict(zip(field_names, values))
        return instance

    @property
    def is_draft_regulation(self):
        return self.regulation_id.startswith("C")

    def __str__(self):
        return str(self.regulation_id)

    @property
    def autocomplete_label(self):
        return f"{self} - {self.information_text}"

    def used_as_terminating_regulation_or_draft_generating_and_terminating_regulation(
        self,
    ):
        if self.role_type != validators.RoleType.BASE:
            return

        return (
            self.measure_set.model.objects.filter(
                terminating_regulation__regulation_id=self.regulation_id,
                terminating_regulation__role_type=self.role_type,
            )
            .exclude(
                generating_regulation__regulation_id__startswith="C",
                generating_regulation__regulation_id=self.regulation_id,
                generating_regulation__role_type=self.role_type,
            )
            .approved_up_to_transaction(transaction=self.transaction)
            .exists()
        )


class Amendment(TrackedModel):
    """
    This regulation amends a base regulation or an antidumping regulation.

    It can affect the tariff and commercial aspects of the updated regulation but it
    does not extend nor close the regulation itself.

    If the modification regulation has no end date of validity, its end date is defined
    by the end date of the regulations it modifies.
    """

    record_code = "290"
    subrecord_code = "00"

    enacting_regulation = models.ForeignKey(
        Regulation,
        on_delete=models.PROTECT,
        related_name="+",
    )
    target_regulation = models.ForeignKey(
        Regulation,
        on_delete=models.PROTECT,
        related_name="amendments",
    )

    identifying_fields = (
        "enacting_regulation__regulation_id",
        "target_regulation__regulation_id",
    )

    business_rules = (UpdateValidity,)


class Extension(TrackedModel):
    """
    Prorogation regulations have no validity period of their own but extend the
    validity end date of a base or modification regulation. This means that the
    measures falling under the prorogued regulation are prorogued as well.

    A prorogation regulation can extend several regulations at different dates and a
    regulation can be extended several times.

    If a regulation has been prorogued, its published end date does not take into
    account the prorogation and is different from its effective end date.

    Prorogation regulations are also called "extension regulations".
    """

    record_code = "295"
    subrecord_code = "00"

    enacting_regulation = models.ForeignKey(
        Regulation,
        on_delete=models.PROTECT,
        related_name="+",
    )
    target_regulation = models.ForeignKey(
        Regulation,
        on_delete=models.PROTECT,
        related_name="extensions",
    )
    effective_end_date = models.DateField(null=True, blank=True)

    identifying_fields = ("enacting_regulation_id", "target_regulation_id")

    business_rules = (UpdateValidity,)


class Suspension(TrackedModel):
    """
    A FTS regulation suspends the applicability of a regulation for a period of
    time.

    This means that all the measures within the regulations are suspended as
    long as the FTS is valid. Once the FTS is abrogated or reaches its validity
    end date, all the measures of the suspended regulation become applicable
    again.
    """

    record_code = "300"
    subrecord_code = "00"
    action_record_code = "305"
    action_subrecord_code = "00"

    enacting_regulation = models.ForeignKey(
        Regulation,
        on_delete=models.PROTECT,
        related_name="+",
    )
    target_regulation = models.ForeignKey(
        Regulation,
        on_delete=models.PROTECT,
        related_name="suspensions",
    )
    effective_end_date = models.DateField(null=True, blank=True)

    identifying_fields = (
        "enacting_regulation__regulation_id",
        "target_regulation__regulation_id",
    )

    business_rules = (UpdateValidity,)


class Termination(TrackedModel):
    """
    This regulation abrogates a base, modification or FTS regulation at a given
    date. It puts an end date to an open ended regulation or brings the already
    existing end date of the regulation further back in time. The end date
    applies by definition to all measures under the abrogated regulation; unless
    these measures have a specific end dates.

    If a regulation has been abrogated, its published end date does not take into
    account the abrogation and is different from its effective end date.

    An explicit abrogation regulation has no validity period; it ends the validity
    period of a measure generating regulation or an FTS regulation.
    """

    record_code = "280"
    subrecord_code = "00"

    enacting_regulation = models.ForeignKey(
        Regulation,
        on_delete=models.PROTECT,
        related_name="+",
    )
    target_regulation = models.ForeignKey(
        Regulation,
        on_delete=models.PROTECT,
        related_name="terminations",
    )
    effective_date = models.DateField()

    identifying_fields = ("enacting_regulation_id", "target_regulation_id")

    business_rules = (UpdateValidity,)


class Replacement(TrackedModel):
    """
    This record holds the information specifying which draft regulations are
    replaced by a definitive regulation.

    Regulations can be partially replaced, based on any one (or a combination)
    of the following three elements: measure type id, geographical area id and
    chapter heading.
    """

    record_code = "305"
    subrecord_code = "00"

    enacting_regulation = models.ForeignKey(
        Regulation,
        on_delete=models.PROTECT,
        related_name="+",
    )
    target_regulation = models.ForeignKey(
        Regulation,
        on_delete=models.PROTECT,
        related_name="replacements",
    )

    measure_type_id = models.CharField(
        max_length=6,
        validators=[measure_type_id_validator],
        null=True,
        blank=True,
    )
    geographical_area_id = models.CharField(
        max_length=4,
        validators=[area_id_validator],
        null=True,
        blank=True,
    )
    chapter_heading = models.CharField(max_length=2, null=True, blank=True)

    identifying_fields = ("enacting_regulation_id", "target_regulation_id")

    business_rules = (UpdateValidity,)
