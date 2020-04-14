from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import RangeOperators
from django.db import models
from treebeard.mp_tree import MP_Node

from common.models import TimestampedMixin, ValidityMixin


class Commodity(MP_Node, TimestampedMixin, ValidityMixin):
    code = models.CharField(max_length=12)

    description = models.TextField()
    predecessor = models.OneToOneField(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="successor",
    )
    version = models.PositiveIntegerField()

    def get_live_children(self, **kwargs):
        return self.get_children().filter(live=True, **kwargs)

    def get_measures(self):
        if self.measures.exists():
            return self.measures.all()
        query = self.get_ancestors().filter(measures__isnull=False)
        if query.exists():
            return query.first().measures.all()

        return False

    def has_measure_in_tree(self):
        ascendant_measures = self.get_ancestors().filter(measures__isnull=False)
        descendant_measures = self.get_descendants().filter(measures__isnull=False)
        return (
            self.measures.exists()
            or ascendant_measures.exists()
            or descendant_measures.exists()
        )

    class Meta:
        constraints = (
            ExclusionConstraint(
                name="exclude_overlapping_commodities",
                expressions=[
                    ("valid_between", RangeOperators.OVERLAPS),
                    ("code", RangeOperators.EQUAL),
                ],
            ),
        )
