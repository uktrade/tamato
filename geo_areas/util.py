from django.db import models


def with_latest_description_string(qs):
    """Returns a queryset annotate with its latest description's validity_start
    date, filtered by this date and then annotated with that latest description
    object's description field value."""
    return (
        qs.annotate(
            latest_transaction_order=models.Max(
                "descriptions__version_group__current_version__transaction__order",
            ),
        )
        .filter(
            descriptions__version_group__current_version__transaction__order=models.F(
                "latest_transaction_order",
            ),
        )
        .annotate(
            description=models.F(
                "descriptions__description",
            ),
        )
    )
