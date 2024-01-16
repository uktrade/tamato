from django.db.models import BooleanField
from django.db.models import Case
from django.db.models import OuterRef
from django.db.models import Subquery
from django.db.models import When

from common.models.tracked_qs import TrackedModelQuerySet


class QuotaOrderNumberQuerySet(TrackedModelQuerySet):
    def with_is_origin_quota(self) -> TrackedModelQuerySet:
        """Annotates the query set with a boolean stating whether the quota is
        an origin quota (and has required certificates)."""
        return self.annotate(
            origin_quota=Case(
                When(required_certificates__isnull=False, then=True),
                default=False,
                output_field=BooleanField(),
            ),
        )


class QuotaOrderNumberOriginQuerySet(TrackedModelQuerySet):
    def with_latest_geo_area_description(qs):
        """
        Returns a QuotaOrderNumberOrigin queryset annotated with the latest
        result of a GeographicalAreaDescription subquery's description value,
        linking these two queries on version_group field.

        Where an area has multiple current descriptions, the description with
        the latest validity_start date is used.

        See also with_latest_geo_area_description method on
        GeographicalAreaQuerySet
        """
        from geo_areas.models import GeographicalAreaDescription

        current_descriptions = (
            GeographicalAreaDescription.objects.current()
            .filter(
                described_geographicalarea__version_group=OuterRef(
                    "geographical_area__version_group",
                ),
            )
            .order_by("-validity_start")
        )
        return qs.annotate(
            geo_area_description=Subquery(
                current_descriptions.values("description")[:1],
            ),
        )


class QuotaOrderNumberOriginExclusionQuerySet(TrackedModelQuerySet):
    def with_latest_geo_area_description(qs):
        """
        Returns a QuotaOrderNumberOriginExclusion queryset annotated with the
        latest result of a GeographicalAreaDescription subquery's description
        value, linking these two queries on version_group field.

        Where an area has multiple current descriptions, the description with
        the latest validity_start date is used.

        See also with_latest_geo_area_description method on
        GeographicalAreaQuerySet
        """
        from geo_areas.models import GeographicalAreaDescription

        current_descriptions = (
            GeographicalAreaDescription.objects.current()
            .filter(
                described_geographicalarea__version_group=OuterRef(
                    "excluded_geographical_area__version_group",
                ),
            )
            .order_by("-validity_start")
        )
        return qs.annotate(
            geo_area_description=Subquery(
                current_descriptions.values("description")[:1],
            ),
        )
