.. _11-store-and-check-preference-codes:

11. Store and check business rules around preference codes
==========================================================

Date: 2021-02-11

Status
------

Proposed

Context
-------

There are many different mechanisms in the tariff to give traders preferential
access to the market. For example, the same trader might have available to them
a non-preferential (WTO) quota whilst also having access to a preferential rate
from a free trade agreement. The trader also may not wish to use the latter
because of the extra compliance required around rules of origin. In general,
customs systems cannot (and should not) try and apply the "best" tariff.

Traders therefore require some way to specify at the point of declaration what
their preferred treatment is. This is specified using `Box 36 of the SAD form
<https://www.gov.uk/government/publications/uk-trade-tariff-imports-and-community-transport-inwards/uk-trade-tariff-imports-and-community-transport-inwards#box-36---preference>`_.
Traders write a 3-digit preference code in box 36 to specify their desired
treatment, and declaration systems apply the treatment if it is available or
return an error if it is not.

Preference codes are not specified as part of the tariff file. Instead, a
separate correlation table is used that maps preference codes to the measure
types that should be applied. For example, specifying preference code "100"
selects measure type 103 for the Erga Omnes third-country duty.

This mechanism has three extra purposes.

It controls when additional duties get applied
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Any measure type specified against the preference code in the correlation table
is "added on" to the final tariff. So in addition to the third-country duty
(103) specified for preference code "100", safeguard duties (696),
representative price securities (651) and additional CIF duties (652) are also
present. This means that those additional duties (if present) will also be
charged. This is the means by which safeguard quotas can "switch off" the normal
safeguard duty because the preference code for non-preferential quotas does not
include 696 measures.

It controls requirements around presence of supporting measures
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Some preference codes are only valid when two measure types are found together.
For example, the preference code "323" covers preferential tariff quotas subject
to end-use. There are two ways for this preference code to be activated:

* by the presence of an end-use preferential quota (146),
* by the presence of a normal preferential quota (143) and a declaration of
  subheading submitted to end-use provisions measure (464).

The presence of these two measure types in the same table represents an "option"
because 143 and 146 both come from the same measure type series which has its
combination field set to zero, so only one can apply.

It specifies regulation groups
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For each preference code and measure type, the correlation table can specify a
list of regulation groups. The measure generating regulation must then sit in
one of those groups for the preference code to be applicable. For example,
preference code "120" is only applicable when there is a measure with type 122
and regulation group KON. This means that any non-preferential tariff quotas
must always be linked to a regulation in the correct group.

Decision
--------

Tables of the current preference code correlation data will be stored in TaMaTo
using the following schema:

.. code:: python

    class PreferenceCode(TrackedModel, ValidityMixin):
        identifying_fields = ("sid",)

        sid = models.CharField(
          max_length=3,
          help_text="The code used in Box 36 of the SAD form.",
          validators=[RegexValidator(r"[0-9]{3}")],
        )

        name = models.TextField(
          help_text="""A short description of the policy mechanism
            the trader will use through the use of this code.""",
        )

        description = models.TextField(
          help_text="""A detailed description of the general treatment
            the trader will receive through the use of this code or more
            information on the circumstances in which this code applies.""",
        )


    class PreferenceCodeMapping(TrackedModel, ValidityMixin):
        identifying_fields = ("sid",)

        sid = SignedIntSID()

        preference_code = models.ForeignKey(
            PreferenceCode,
            related_name="mappings",
        )

        measure_types = models.ManyToManyField(
            "measures.MeasureType",
            through="PreferenceCodeMappingMeasureType",
            help_text="The measure types required for this mapping to apply.",
        )

        regulation_groups = models.ManyToManyField(
            "regulations.Group",
            through="PreferenceCodeMappingRegulationGroup",
            help_text="""The regulation groups that the generating regulation of
            a measure must have for this mapping to apply to that measure.""",
        )

        condition_codes = models.ManyToManyField(
            "measures.MeasureConditionCode",
            through="PreferenceCodeMappingConditionCode",
            help_text="""The condition codes that the measure condition must have
            one of for this mapping to apply to that measure.""",
        )

        choice_of_types = models.BoolField(
            default=True,
            help_text="""True when any of the attached measure types can be
                present, False when all of the attached measure types must be present.""",
        )


    class PreferenceCodeMappingMeasureType(TrackedModel):
        identifying_fields = ("mapping__id", "measure_type__sid")

        mapping = models.ForeignKey(
            PreferenceCodeMapping,
            related_name="measure_types",
        )

        measure_type = models.ForeignKey(
            "measures.MeasureType",
            related_name="preference_code_mappings",
        )


    class PreferenceCodeMappingRegulationGroup(TrackedModel):
        identifying_fields = ("mapping__id", "regulation_group__group_id")

        mapping = models.ForeignKey(
            PreferenceCodeMapping,
            related_name="regulation_groups",
        )

        regulation_group = models.ForeignKey(
            "regulations.Group",
            related_name="preference_code_mappings",
        )


    class PreferenceCodeMappingConditionCode(TrackedModel):
        identifying_fields = ("mapping__id", "condition_code__code")

        mapping = models.ForeignKey(
            PreferenceCodeMapping,
            related_name="condition_codes",
        )

        condition_code = models.ForeignKey(
            "measures.MeasureConditionCode",
            related_name="preference_code_mappings",
        )


The following business rules will apply to preference codes:

* PC1: The validity start date of a preference code cannot be after the validity
  end date, if defined.

The following business rules will apply to preference code mappings:

* PCM1: The preference code referenced by the preference code mapping must exist.
* PCM2: The validity period of the preference code must span the validity period
  of the preference code mapping.
* PCM3: The validity start date of a preference code mapping cannot be after the
  validity end date, if defined.
* PCM4: Where a preference code mapping references a measure type, the validity
  period of the measure type must span the validity period of the preference
  code mapping.
* PCM5: Where a preference code mapping references a regulation group, the
  validity period of the regulation group must span the validity period of the
  preference code mapping.
* PCM6: Where a preference code mapping references a condition code, the
  validity period of the condition code must span the validity period of the
  preference code mapping.
* PCM6: If a preference code mapping references a measure type along with a
  regulation group, all other preference code mappings (even for other
  preference codes) that reference that measure type must also declare a
  regulation group.

The following business rule will apply to measures:

* ME120: Where a measure's type is used in any preference code mapping, then at
  least one preference code must apply to that measure. This business rule is
  only applicable for measures with start date after 2021-02-11.

A preference code "applies to" a measure if the following are all true:

* If the preference code has a mapping that mentions the measure's type.
* If the mapping has a False choice field, there
  exist measures for all of the other measure types for the same goods
  nomenclature, geographical area, order number, additional code, reduction
  indicator for the validity period of the measure.
* If the mapping declares regulation groups, the regulation group of the
  measure's generating regulation must be one of the declared groups.
* If the mapping declares condition codes, the measure must have conditions that
  use one of the declared condition codes. If the mapping does not declare any
  condition codes then the measure may have any or no conditions.


Consequences
------------

The main motivation for storing preference code tables is to implement ME120.
With this rule, users are prevented from creating measures that traders are
unable to actually declare because there is no valid preference code for them.

The additional motive is that it would allow exposing these tables as
part of citizen-facing services. For the first time it would be possible to
derive what preference codes would be required to use a given measure, if any.
For this reason the human-readable text from the table is also included.

Even though preference codes are not contained in the tariff file and there is
currently no way of communicating desired changes to them, any changes do
need to be tracked and have the usual date-based validity rules apply. This is
because if one day the correlation is changed ME120 will still need to be
able to refer to previous versions of the table for use against old measures. It
is clear from the text version of the correlation table that changes to both the
codes and the mappings are possible independently.

Note that the interaction with condition codes is currently not very interesting
because in the current version of the table there are no measure types with
conditions that do not also have a counterpart without conditions – hence from
an ME120 perspective the conditions make no difference.
