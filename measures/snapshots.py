from dataclasses import dataclass
from datetime import date
from datetime import timedelta

from commodities.models.dc import Commodity
from commodities.models.dc import CommodityCollection
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
    def _get_snapshot_from_tree(
        cls,
        collection: CommodityCollection,
        as_at: date,
        transaction: Transaction,
    ):
        tree = collection._get_snapshot(transaction, as_at)
        # `None` is not a bug! We want the commodity code tree to be
        # linked to a specific date, but the measure date actually
        # represents a range of dates, and not a specific one.
        return cls(SnapshotMoment(transaction, None), tree)

    @classmethod
    def get_snapshots(cls, measure: Measure, transaction: Transaction):
        """
        Yield a MeasureSnapshot for each commodity tree that contains the goods
        nomenclature on the measure.

        It is possible for the commodity tree to change over the lifetime of the
        measure, so this method will yield a snapshot for each of the commodity
        trees that existed over that lifetime.
        """
        loader = CommodityCollectionLoader(
            prefix=measure.goods_nomenclature.code.chapter,
        )
        collection = loader.load()

        snapshot = cls._get_snapshot_from_tree(
            collection,
            measure.effective_valid_between.lower,
            transaction,
        )
        yield snapshot

        while measure.effective_valid_between.upper_is_greater(snapshot.extent):
            snapshot = cls._get_snapshot_from_tree(
                collection,
                snapshot.extent.upper + timedelta(days=1),
                transaction,
            )
            yield snapshot
