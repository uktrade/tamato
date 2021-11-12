from django.db.models import BooleanField
from django.db.models import Case
from django.db.models import When

from common.models.trackedmodel_queryset import TrackedModelQuerySet


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
