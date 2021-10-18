from django.db import models

from common.models.mixins import TimestampedMixin


class VersionGroup(TimestampedMixin):
    current_version = models.OneToOneField(
        "common.TrackedModel",
        on_delete=models.SET_NULL,
        null=True,
        related_query_name="is_current",
    )

    def update_current_version(self, version: TrackedModel) -> None:
        self.current_version = version
        self.save()
