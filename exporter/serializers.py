import logging
import os
from collections import defaultdict
from collections import namedtuple
from typing import Dict
from typing import List
from typing import Sequence

from django.conf import settings
from lxml import etree

from common.serializers import EnvelopeSerializer
from common.serializers import TaricDataAssertionError
from common.serializers import validate_envelope

logger = logging.getLogger(__name__)

# RenderedTransactions
RenderedTransactions = namedtuple(
    "RenderedTransactions",
    ("envelope_id", "output", "transactions", "is_oversize", "max_envelope_size"),
)
RenderedTransactions.__doc__ = """\
Transient object that links Transaction objects to the file like object they were rendered to as Envelope XML.

This enables separation of serialization, validation and saving to the database.
Any of the steps prior to saving to the database may fail fail without incurring a roll-back.

:param envelope_id: Envelope ID, to use later, when creating Envelope objects in the database.
:param output:  file, or file like object Envelope XML was streamed to.
:param transactions: Transaction objects that were rendered to XML in this Envelope.
:param is_oversize: True if the rendered XML was larger than max_size when rendered.
:param max_envelope_size: Maximum envelope size used when rendering this Envelope.
"""


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
        # Transactions with no tracked models can occur if a workbasket
        # is created and then populated, these are filtered as an empty
        # transaction will cause an XSD validation error later on.
        full_transactions = transactions.not_empty().with_xml()
        for transaction in full_transactions.iterator(
            settings.EXPORTER_MAXIMUM_DATABASE_CHUNK,
        ):
            envelope_body = transaction.xml
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

            current_transactions.append(transaction.pk)

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
    """Envelope was bigger than max_envelope_size."""


def validate_rendered_envelopes(
    rendered_envelopes: Sequence[RenderedTransactions],
) -> Dict[int, List[Exception]]:
    """
    Given a sequence of RenderedTransactions, check the envelope data in their
    `output` file objects is valid Envelope XML.

    :param rendered_envelopes: sequence of RenderedEnvelope
    :return: dict of {envelope_id: [Exception,...]}
    """
    envelope_errors = defaultdict(list)
    for rendered_envelope in rendered_envelopes:
        if rendered_envelope.is_oversize:
            envelope_errors[rendered_envelope.envelope_id].append(
                EnvelopeTooLarge(
                    "Envelope Too Big: {rendered_envelope.envelope_id} > {rendered_envelope.max_envelope_size}",
                ),
            )

        envelope_file = rendered_envelope.output
        envelope_file.seek(0, os.SEEK_SET)
        try:
            validate_envelope(envelope_file)
        except (TaricDataAssertionError, etree.DocumentInvalid) as e:
            # Nothing to log here; validate_envelope already logged the issue.
            envelope_errors[rendered_envelope.envelope_id].append(e)
        except BaseException as e:
            logger.exception(e)
            envelope_errors[rendered_envelope.envelope_id].append(e)
    return dict(envelope_errors)
