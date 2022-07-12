from django.db import models


def with_latest_description_string(qs):
    """Returns a queryset annotate with its latest description's validity_start
    date, filtered by this date and then annotated with that latest description
    object's description field value."""
    return (
        qs.annotate(latest_description_date=models.Max("descriptions__validity_start"))
        .filter(descriptions__validity_start=models.F("latest_description_date"))
        .annotate(
            description=models.F(
                "descriptions__description",
            ),
        )
    )
