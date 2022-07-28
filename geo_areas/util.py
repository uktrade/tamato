from django.db.models import OuterRef
from django.db.models import Subquery

from geo_areas.models import GeographicalAreaDescription


def with_current_description(qs):
    """Returns a GeographicalArea queryset annotated with the latest result of a
    GeographicalAreaDescription subquery's description value, linking these two
    queries on version_group field."""
    current_descriptions = (
        GeographicalAreaDescription.objects.current()
        .filter(described_geographicalarea__version_group=OuterRef("version_group"))
        .order_by("transaction__order")
    )
    return qs.annotate(
        description=Subquery(current_descriptions.values("description")[:1]),
    )
