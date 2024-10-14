from django.db import models
from psycopg.types.range import DateRange


class RegulationsAmendment(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    enacting_regulation = models.ForeignKey("RegulationsRegulation", models.DO_NOTHING)
    target_regulation = models.ForeignKey(
        "RegulationsRegulation",
        models.DO_NOTHING,
        related_name="regulationsamendment_target_regulation_set",
    )


class RegulationsGroup(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange
    group_id = models.CharField(max_length=3)
    description = models.CharField(max_length=500, blank=True, null=True)


class RegulationsRegulation(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    role_type = models.IntegerField()
    regulation_id = models.CharField(max_length=8)
    official_journal_number = models.CharField(max_length=5, blank=True, null=True)
    official_journal_page = models.SmallIntegerField(blank=True, null=True)
    published_at = models.DateField(blank=True, null=True)
    information_text = models.CharField(max_length=500, blank=True, null=True)
    public_identifier = models.CharField(max_length=50, blank=True, null=True)
    url = models.CharField(max_length=200, blank=True, null=True)
    approved = models.BooleanField()
    replacement_indicator = models.IntegerField()
    valid_between = models.TextField(
        blank=True,
        null=True,
    )  # This field type is a guess.
    effective_end_date = models.DateField(blank=True, null=True)
    stopped = models.BooleanField()
    community_code = models.IntegerField(blank=True, null=True)
    regulation_group = models.ForeignKey(
        RegulationsGroup,
        models.DO_NOTHING,
        blank=True,
        null=True,
    )


class RegulationsSuspension(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    effective_end_date = models.DateField(blank=True, null=True)
    enacting_regulation = models.ForeignKey(RegulationsRegulation, models.DO_NOTHING)
    target_regulation = models.ForeignKey(
        RegulationsRegulation,
        models.DO_NOTHING,
        related_name="regulationssuspension_target_regulation_set",
    )


class RegulationsReplacement(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    measure_type_id = models.CharField(max_length=6, blank=True, null=True)
    geographical_area_id = models.CharField(max_length=4, blank=True, null=True)
    chapter_heading = models.CharField(max_length=2, blank=True, null=True)
    enacting_regulation = models.ForeignKey(RegulationsRegulation, models.DO_NOTHING)
    target_regulation = models.ForeignKey(
        RegulationsRegulation,
        models.DO_NOTHING,
        related_name="regulationsreplacement_target_regulation_set",
    )
