"""Common field types."""
from django.contrib.postgres.fields import DateTimeRangeField
from django.db import models

from common import validators
from common.util import TaricDateTimeRange


class NumericSID(models.PositiveIntegerField):
    def __init__(self, *args, **kwargs):
        kwargs["editable"] = False
        kwargs["validators"] = [validators.NumericSIDValidator()]
        kwargs["db_index"] = True
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs["editable"]
        del kwargs["validators"]
        del kwargs["db_index"]
        return name, path, args, kwargs


class SignedIntSID(models.IntegerField):
    def __init__(self, *args, **kwargs):
        kwargs["editable"] = False
        kwargs["db_index"] = True
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs["editable"]
        del kwargs["db_index"]
        return name, path, args, kwargs


class ShortDescription(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 500
        kwargs["blank"] = True
        kwargs["null"] = True
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs["max_length"]
        del kwargs["blank"]
        del kwargs["null"]
        return name, path, args, kwargs


class ApplicabilityCode(models.PositiveSmallIntegerField):
    def __init__(self, *args, **kwargs):
        kwargs["choices"] = validators.ApplicabilityCode.choices
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs["choices"]
        return name, path, args, kwargs


class TaricDateTimeRangeField(DateTimeRangeField):
    range_type = TaricDateTimeRange
