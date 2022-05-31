"""
This is a "run once" script to transition imports out of their RUNNING status
that can be correctly manipulated via existing Django management commands.

In order to run this script, from a Tamato virtualenv:

    python manage.py runscript data_patches.TP2000_338_set_chunks_status
"""


from datetime import datetime

from django.db.transaction import atomic

from importer.models import ImportBatch
from importer.models import ImporterChunkStatus
from importer.models import ImporterXMLChunk


@atomic
def set_chunks_status(batch, status):
    """
    Transition chunks of a batch import to status.

    If any chunks for a batch are in DONE status then more sophisticated remaial
    effor is required than this function offers and so an exception will be
    raised.
    """
    batch_chunks = ImporterXMLChunk.objects.filter(batch=batch)
    print(f"'{batch}' has {batch_chunks.count()} chunk(s).")

    if batch_chunks.filter(status=ImporterChunkStatus.DONE):
        raise Exception(f"ERROR: '{batch}' already has chunks in DONE status.")

    for chunk in batch_chunks:
        old_status = ImporterChunkStatus(chunk.status)
        print(
            f"Transitioning '{chunk}' from {old_status.name} to {status.name}",
        )
        chunk.status = status
        chunk.save()


def run():
    """
    Function called by django_extentions runscript management command:

    https://django-extensions.readthedocs.io/en/latest/runscript.html
    """
    print(f"{datetime.now()} starting batch status transitions...")

    # Transition to ERRORED in preparation for a second import attempt.
    batch_220039 = ImportBatch.objects.get(name="Batch 220039")
    set_chunks_status(batch_220039, ImporterChunkStatus.ERRORED)

    # Transition to ERRORED in preparation for a second import attempt.
    batch_j_and_g = ImportBatch.objects.get(name="Jersey_Guernsey Test File")
    set_chunks_status(batch_j_and_g, ImporterChunkStatus.ERRORED)

    print(f"{datetime.now()} completed transitions.")
