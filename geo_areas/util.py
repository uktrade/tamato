from django.db.models import OuterRef
from django.db.models import Subquery

from geo_areas.models import GeographicalAreaDescription


def with_current_description(qs):
    current_descriptions = (
        GeographicalAreaDescription.objects.current()
        .filter(described_geographicalarea__version_group=OuterRef("version_group"))
        .order_by("transaction__order")
    )
    return qs.annotate(
        description=Subquery(current_descriptions.values("description")[:1]),
    )
