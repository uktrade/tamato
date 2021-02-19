# XXX need to keep this file for migrations to work. delete later.
from datetime import date
from typing import Optional

from django.db import models
from django.db.models import QuerySet

from common.models.transactions import Transaction
from taric import validators


class EnvelopeQuerySet(QuerySet):
    def envelopes_by_year(self, year: Optional[int] = None):
        """Return all envelopes for a year, defaulting to this year.

        :param year: int year, defaults to this year.

        Limitation:  This queries envelope_id which only stores two digit dates.
        """
        if year is None:
            now = date.today()
        else:
            now = date(year, 1, 1)

        return self.order_by("envelope_id").filter(envelope_id__startswith=f"{now:%y}")


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

    objects = EnvelopeQuerySet.as_manager()

    envelope_id = EnvelopeId(unique=True)
    transactions = models.ManyToManyField(
        Transaction,
        related_name="envelopes",
        through="EnvelopeTransaction",
    )

    @classmethod
    def new_envelope(cls):
        """New Envelope instance.  Populates envelope_id."""
        envelope = cls.objects.envelopes_by_year().last()

        if envelope is None:
            # First envelope of the year.
            now = date.today()
            counter = 1
        else:
            year = int(envelope.envelope_id[:2])
            counter = int(envelope.envelope_id[2:]) + 1

            if counter > 9999:
                raise ValueError(
                    "Cannot create more than 9999 Envelopes on a single year."
                )

            now = date(year, 1, 1)

        envelope_id = f"{now:%y}{counter:04d}"
        new_instance = cls.objects.create(envelope_id=envelope_id)
        return new_instance

    def __repr__(self):
        envelope_id = self.envelope_id
        return f'<Envelope: envelope_id="{envelope_id}">'

    class Meta:
        ordering = ("envelope_id",)


class EnvelopeTransaction(models.Model):
    """Applies a sequence to Transactions contained in an Envelope."""

    order = models.IntegerField()
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE)
    envelope = models.ForeignKey(Envelope, on_delete=models.CASCADE)

    class Meta:
        ordering = ("order",)
