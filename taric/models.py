import json

from django.core.serializers.json import DjangoJSONEncoder
from django.db import models

from common.models import TimestampedMixin
from taric import validators


class Transaction(TimestampedMixin):
    def to_json(self):
        """Used for serializing to the session"""

        data = {key: val for key, val in self.__dict__.items() if key != "_state"}
        return json.dumps(data, cls=DjangoJSONEncoder)


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


class Envelope(models.Model):
    """Represents a TARIC3 envelope

    An Envelope contains one or more Transactions, listing changes to be applied to the
    tariff in the sequence defined by the transaction IDs.
    """

    # Max size is 50 megabytes
    MAX_FILE_SIZE = 50 * 1024 * 1024

    envelope_id = EnvelopeId()
    transactions = models.ManyToManyField(
        Transaction, related_name="envelopes", through="EnvelopeTransaction"
    )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"DIT{self.envelope_id}"


class EnvelopeTransaction(models.Model):
    """Applies a sequence to Transactions contained in an Envelope."""

    index = models.IntegerField()
    transaction = models.ForeignKey(Transaction, on_delete=models.PROTECT)
    envelope = models.ForeignKey(Envelope, on_delete=models.PROTECT)
