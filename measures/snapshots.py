from dataclasses import dataclass
from datetime import timedelta

from commodities.models.dc import Commodity
from commodities.models.dc import CommodityCollectionLoader
from commodities.models.dc import CommodityTreeSnapshot
from commodities.models.dc import SnapshotMoment
from common.models.transactions import Transaction
from measures.models import Measure
from measures.querysets import MeasuresQuerySet


@dataclass
class MeasureSnapshot:
    """Represents a set of measures that apply to a part of the commodity tree
    at a given date and transaction."""

    moment: SnapshotMoment
    tree: CommodityTreeSnapshot

    @property
    def extent(self):
        """Returns the date range for which the snapshot is correct."""
        return self.tree.extent

    def get_measures(self, *commodities: Commodity) -> MeasuresQuerySet:
        """Returns the measures attached to the given commodities."""
        return self.tree.get_dependent_measures(*commodities, as_at=self.moment.date)

    def get_applicable_measures(self, commodity: Commodity) -> MeasuresQuerySet:
        """Returns the mesures that apply to the commodity (i.e. any defined on
        it or one of its ancestors)."""
        return self.get_measures(commodity, *self.tree.get_ancestors(commodity))

    def get_branch_measures(self, commodity: Commodity) -> MeasuresQuerySet:
        """Returns the measures that are within the same tree branch as the
        commodity (i.e. any defined on it, its ancestors or any of its
        descendants)."""
        return self.get_measures(
            commodity,
            *self.tree.get_ancestors(commodity),
            *self.tree.get_descendants(commodity),
        )

    def overlaps(self, measure: Measure) -> MeasuresQuerySet:
        """
        Returns the measures that overlap with the passed measure.

        The MeasureSnapshot must have been created with a commodity tree that
        contains the goods nomenclature on the measure, otherwise this method
        will return an empty set.
        """
        commodity = self.tree.get_commodity(
            measure.goods_nomenclature.item_id,
            measure.goods_nomenclature.suffix,
        )

        if not commodity:
            return Measure.objects.none()

        valid_between = measure.effective_valid_between
        return (
            self.get_branch_measures(commodity)
            .with_effective_valid_between()
            .excluding_versions_of(measure.version_group)
            .filter(db_effective_valid_between__overlap=valid_between)
        )

    @classmethod
    def get_snapshots(
        cls,
        measure: Measure,
        transaction: Transaction,
    ) -> "MeasureSnapshot":
        """
        Generator that yields a MeasureSnapshot for each commodity tree that
        contains the goods nomenclature on the measure.

        It is possible for the commodity tree to change over the lifetime of the
        measure, so this method will yield a snapshot for each of the commodity
        trees that existed over that lifetime.
        """

        collection = CommodityCollectionLoader(
            prefix=measure.goods_nomenclature.code.chapter,
        ).load()

        snapshot_date = measure.effective_valid_between.lower

        while True:
            # Set SnapshotMoment.date to None on the SnapshotMoment instance
            # since measure date ranges are used to filter the comm code tree.
            snapshot = MeasureSnapshot(
                SnapshotMoment(transaction, None),
                collection.get_snapshot(transaction, snapshot_date),
            )

            yield snapshot

            # See `CommodityTreeSnapshot.extent()` for a definition of extent.
            snapshot_extent = snapshot.extent
            if measure.effective_valid_between.upper_is_greater(snapshot_extent):
                snapshot_date = snapshot_extent.upper + timedelta(days=1)
            else:
                break
