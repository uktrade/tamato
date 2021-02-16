# XXX need to keep this file for migrations to work. delete later.
from django.db import models

from common.models.transactions import Transaction
from taric import validators


class EnvelopeId(models.CharField):
    """An envelope ID must match the format YYxxxx, where YY is the last two
    digits of the current year and xxxx is a zero padded integer, incrementing
    from 0001 for the first envelope of the year."""

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
    """
    Represents a TARIC3 envelope.

    An Envelope contains one or more Transactions, listing changes to be applied
    to the tariff in the sequence defined by the transaction IDs.
    """

    envelope_id = EnvelopeId(unique=True)
    transactions = models.ManyToManyField(
        Transaction,
        related_name="envelopes",
        through="EnvelopeTransaction",
    )


class EnvelopeTransaction(models.Model):
    """Applies a sequence to Transactions contained in an Envelope."""

    order = models.IntegerField()
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE)
    envelope = models.ForeignKey(Envelope, on_delete=models.CASCADE)

    class Meta:
        ordering = ("order",)
