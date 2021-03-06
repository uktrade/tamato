"""
These models are for testing purposes only and will not be
migrated into the database outside of a test environment.
"""
from django.db import models

from common.models import TrackedModel
from common.models import ValidityMixin


class TestModel1(TrackedModel, ValidityMixin):
    __test__ = False
    record_code = "01"
    subrecord_code = "01"

    taric_template = "test_template"

    sid = models.PositiveIntegerField()
    name = models.CharField(max_length=24, null=True)


class TestModel2(TrackedModel, ValidityMixin):
    __test__ = False
    record_code = "02"
    subrecord_code = "01"

    custom_sid = models.PositiveIntegerField()
    description = models.CharField(max_length=24, null=True)

    identifying_fields = ("custom_sid",)


class TestModel3(TrackedModel, ValidityMixin):
    __test__ = False
    record_code = "03"
    subrecord_code = "01"

    sid = models.PositiveIntegerField()
    linked_model = models.ForeignKey(TestModel1, on_delete=models.PROTECT)
