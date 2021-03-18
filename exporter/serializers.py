import logging
import os
from collections import namedtuple
from typing import Dict
from typing import Sequence

from lxml import etree

from common.serializers import EnvelopeSerializer
from common.serializers import TaricDataAssertionError
from common.serializers import validate_envelope

logger = logging.getLogger(__name__)

# RenderedTransactions
RenderedTransactions = namedtuple(
    "RenderedTransactions",
    "envelope_id output transactions is_oversize max_envelope_size",
)


class MultiFileEnvelopeTransactionSerializer(EnvelopeSerializer):
    """
    Streaming EnvelopeSerializer that with multiple streams.

    On reaching a size boundary, the current envelope is completed, the next
    stream from outputs is selected new envelope output starts.
    """

    def __init__(
        self,
        output_constructor: callable,
        envelope_id=1,
        *args,
        **kwargs,
    ) -> None:
        self.output_constructor = output_constructor
        EnvelopeSerializer.__init__(
            self, self.output_constructor(), envelope_id=envelope_id, *args, **kwargs
        )

    def start_next_envelope(self):
        self.output = self.output_constructor()
        super().start_next_envelope()

    def split_render_transactions(self, transactions):
        """
        :param transactions: Transaction

        Write tracked_models of transactions out to one or more envelopes.
        An individual Transaction will not be split

        yields instances of RenderedTransaction
        """
        self.write(self.render_file_header())
        self.write(self.render_envelope_start())

        envelope_extra_size = self.envelope_start_size + self.envelope_end_size

        # Transactions written to the current output
        current_transactions = []
        for transaction in transactions.all():
            tracked_models = transaction.tracked_models.all()
            if not tracked_models.count():
                # Transactions with no tracked models can occur if a workbasket
                # is created and then populated, these are filtered as an empty
                # transaction will cause an XSD validation error later on.
                #
                # Django bug 2361  https://code.djangoproject.com/ticket/2361
                #   Queryset.filter(m2mfield__isnull=False) may duplicate records,
                #   so cannot be used, instead the count() of each tracked_models
                #   resultset is checked.
                #
                #
                continue

            envelope_body = self.render_envelope_body(tracked_models, transaction.order)
            envelope_body_size = len(envelope_body.encode())
            if self.is_envelope_full(envelope_body_size):
                oversize = not self.can_fit_one_envelope(
                    envelope_body_size + envelope_extra_size,
                )

                # Finish previous envelope and yield output and list of contained transactions
                self.write(self.render_envelope_end())

                yield RenderedTransactions(
                    envelope_id=self.envelope_id,
                    output=self.output,
                    transactions=current_transactions,
                    is_oversize=oversize,
                    max_envelope_size=self.max_envelope_size,
                )

                # Start new envelope
                self.start_next_envelope()
                current_transactions = []
                self.write(self.render_file_header())
                self.write(self.render_envelope_start())

            current_transactions.append(transaction)

            self.write(envelope_body)

        self.write(self.render_envelope_end())
        yield RenderedTransactions(
            envelope_id=self.envelope_id,
            output=self.output,
            transactions=current_transactions,
            is_oversize=False,
            max_envelope_size=self.max_envelope_size,
        )


class EnvelopeTooLarge(Exception):
    pass


def validate_rendered_envelopes(
    rendered_envelopes: Sequence[RenderedTransactions],
) -> Dict[int, Exception]:
    """
    :param rendered_envelopes: sequence of RenderedEnvelope
    :return: dict of {envelope_id: Exception}
    """
    invalid_envelopes = {}
    for rendered_envelope in rendered_envelopes:
        if rendered_envelope.is_oversize:
            invalid_envelopes[rendered_envelope.envelope_id] = EnvelopeTooLarge(
                "Envelope Too Big: {rendered_envelope.envelope_id} > {rendered_envelope.max_envelope_size}",
            )

        envelope_file = rendered_envelope.output
        envelope_file.seek(0, os.SEEK_SET)
        try:
            validate_envelope(envelope_file)
        except (TaricDataAssertionError, etree.DocumentInvalid) as e:
            # Nothing to log here - validate_envelope has already logged the issue.
            invalid_envelopes[rendered_envelope.envelope_id] = e
        except BaseException as e:
            logger.exception(e)
            invalid_envelopes[rendered_envelope.envelope_id] = e
    return invalid_envelopes
