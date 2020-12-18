"""Mixins for models."""
from django.contrib.postgres.fields import DateTimeRangeField
from django.db import models


class TimestampedMixin(models.Model):
    """Mixin adding timestamps for creation and last update."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ValidityMixin(models.Model):
    """Mixin for models with validity periods."""

    valid_between = DateTimeRangeField()

    class Meta:
        abstract = True
