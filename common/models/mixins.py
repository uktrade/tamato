"""Mixins for models."""
from django.db import models

from common.fields import TaricDateRangeField


class TimestampedMixin(models.Model):
    """Mixin adding timestamps for creation and last update."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ValidityMixin(models.Model):
    """Mixin for models with validity periods."""

    valid_between = TaricDateRangeField(db_index=True)

    class Meta:
        abstract = True
