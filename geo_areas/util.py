from django.db import models


def with_description_string(qs):
    """Returns a queryset annotated with description object's description field
    value."""
    return qs.annotate(
        description=models.F(
            "descriptions__description",
        ),
    )
