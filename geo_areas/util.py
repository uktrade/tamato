from django.db import models


def with_description_string(qs):
    """If a description object has no description value, return an empty string,
    else return description value."""
    return qs.exclude(descriptions__description__isnull=True).annotate(
        description=models.F(
            "descriptions__description",
        ),
    )
