from django.db import models


def with_description_string(qs):
    """If a description object has no description value, return an empty string,
    else return description value."""
    return qs.annotate(
        description=models.Case(
            models.When(
                descriptions__description__isnull=True,
                then=models.Value(""),
            ),
            default=models.F(
                "descriptions__description",
            ),
        ),
    )
