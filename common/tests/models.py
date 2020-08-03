"""
These models are for testing purposes only and will not be
migrated into the database outside of a test environment.
"""
from django.db import models

from common.models import TrackedModel
from common.models import ValidityMixin


class TestModel1(TrackedModel, ValidityMixin):
    __test__ = False
    sid = models.PositiveIntegerField()
    name = models.CharField(max_length=24, null=True)


class TestModel2(TrackedModel, ValidityMixin):
    __test__ = False
    custom_sid = models.PositiveIntegerField()
    description = models.CharField(max_length=24, null=True)

    identifying_fields = ("custom_sid",)
