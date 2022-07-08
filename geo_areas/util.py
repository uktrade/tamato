from django.db import models


def with_latest_description_string(qs):
    """Returns a queryset annotated with the latest validity_start date and
    current version, filtered by these values and then annotated with that
    latest description object's description field value."""
    return (
        qs.annotate(
            description_current_version=models.Max(
                "descriptions__version_group__current_version__pk",
            ),
            latest_description_date=models.Max("descriptions__validity_start"),
        )
        .filter(
            descriptions__version_group__current_version__pk=models.F(
                "description_current_version",
            ),
            descriptions__validity_start=models.F("latest_description_date"),
        )
        .annotate(
            description=models.F(
                "descriptions__description",
            ),
        )
    )
