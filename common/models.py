from django.contrib.postgres.fields import DateTimeRangeField
from django.db import models


class TimestampedMixin(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ValidityMixin(models.Model):
    valid_between = DateTimeRangeField()
    live = models.BooleanField(default=False)

    class Meta:
        abstract = True
