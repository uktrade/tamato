import os
import sys
from typing import Optional
from typing import Sequence

from lxml import etree

from common.models import Transaction
from common.serializers import validate_envelope
from exporter.serializers import MultiFileEnvelopeTransactionSerializer
from exporter.util import dit_file_generator
from exporter.util import item_timer

# VARIATION_SELECTOR enables emoji presentation
WARNING_SIGN_EMOJI = "\N{WARNING SIGN}\N{VARIATION SELECTOR-16}"


def dump_transactions(
    transactions: Sequence[Transaction],
    envelope_id: int,
    directory: str,
    max_envelope_size: Optional[int],
    output_stream=None,
):
    """
    Dump transactions to envelope files in specified directory.

    :param transactions:  Transactions to be pack into envelopes
    :param envelope_id:  First envelope id to use
    :param directory:  Directory to write envelope files to.
    :param max_envelope_size:  Maximum envelope size in bytes, or None to disable splitting.
    :param output_stream:  Stream to write output status messages to, defaults to stdout.

    See `EnvelopeSerializer` for more information on splitting by size.
    """

    if output_stream is None:
        output_stream = sys.stdout

    output_file_constructor = dit_file_generator(directory, envelope_id)
    serializer = MultiFileEnvelopeTransactionSerializer(
        output_file_constructor,
        envelope_id=envelope_id,
        max_envelope_size=max_envelope_size,
    )
    errors = False
    for time_to_render, rendered_envelope in item_timer(
        serializer.split_render_transactions(transactions),
    ):
        envelope_file = rendered_envelope.output
        if not rendered_envelope.transactions:
            output_stream.write(
                f"{envelope_file.name} {WARNING_SIGN_EMOJI}  is empty !",
            )
            errors = True
        else:
            envelope_file.seek(0, os.SEEK_SET)
            try:
                validate_envelope(envelope_file)
                assert 0
            except etree.DocumentInvalid:
                output_stream.write(
                    f"{envelope_file.name} {WARNING_SIGN_EMOJI}️ Envelope invalid:",
                )
            else:
                total_transactions = len(rendered_envelope.transactions)
                output_stream.write(
                    f"{envelope_file.name} \N{WHITE HEAVY CHECK MARK} XML valid. {total_transactions} transactions, serialized in {time_to_render:.2f} seconds using {envelope_file.tell()} bytes.",
                )
    return not errors
