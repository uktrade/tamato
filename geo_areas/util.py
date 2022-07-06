from django.db import models


def with_latest_description_string(qs):
    """Returns a queryset annotated with the latest validity_start date and
    latest transaction order number, filtered by these values and then annotated
    with that latest description object's description field value."""
    return (
        qs.annotate(
            latest_transaction_order=models.Max(
                "descriptions__version_group__current_version__transaction__order",
            ),
            latest_description_date=models.Max("descriptions__validity_start"),
        )
        .filter(
            descriptions__version_group__current_version__transaction__order=models.F(
                "latest_transaction_order",
            ),
            descriptions__validity_start=models.F("latest_description_date"),
        )
        .annotate(
            description=models.F(
                "descriptions__description",
            ),
        )
    )
