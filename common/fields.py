from django.db import models

from common import validators


class NumericSID(models.PositiveIntegerField):
    def __init__(self, *args, **kwargs):
        kwargs["editable"] = False
        kwargs["validators"] = [validators.NumericSIDValidator()]
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs["editable"]
        del kwargs["validators"]
        return name, path, args, kwargs


class SignedIntSID(models.IntegerField):
    def __init__(self, *args, **kwargs):
        kwargs["editable"] = False
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs["editable"]
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
