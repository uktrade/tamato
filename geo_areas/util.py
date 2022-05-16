from django.db import models


def with_latest_description_string(qs):
    """Returns a queryset annotated with description object's description field
    value."""
    return (
        qs.annotate(latest_date=models.Max("descriptions__validity_start"))
        .filter(descriptions__validity_start=models.F("latest_date"))
        .annotate(
            description=models.F(
                "descriptions__description",
            ),
        )
    )
