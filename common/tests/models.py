"""
These models are for testing purposes only and will not be
migrated into the database outside of a test environment.
"""

from django.db import models

from common.models import ValidityMixin, TrackedModel


class TestModel1(TrackedModel, ValidityMixin):
    sid = models.PositiveIntegerField()
    name = models.CharField(max_length=24, null=True)


class TestModel2(TrackedModel, ValidityMixin):
    custom_sid = models.PositiveIntegerField()
    description = models.CharField(max_length=24, null=True)

    identifying_fields = ("custom_sid",)
