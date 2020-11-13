# XXX need to keep this file for migrations to work. delete later.
from django.db import models

from taric import validators


class EnvelopeId(models.CharField):
    """An envelope ID must match the format YYxxxx, where YY is the last two digits of
    the current year and xxxx is a zero padded integer, incrementing from 0001 for the
    first envelope of the year.
    """

    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 6
        kwargs["validators"] = [validators.EnvelopeIdValidator]
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs["max_length"]
        del kwargs["validators"]
        return name, path, args, kwargs
