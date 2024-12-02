import time
from datetime import date

from commodities.models.dc import CommodityCollectionLoader
from commodities.models.dc import CommodityTreeSnapshot
from commodities.models.dc import SnapshotMoment
from open_data.models import ReportGoodsNomenclature


def tree_edge_to_db(tree_edges):
    for comm in tree_edges:
        parent = tree_edges[comm]
        if parent:
            parent_obj_pk = parent.obj.pk
        else:
            parent_obj_pk = None
        try:
            commodity = ReportGoodsNomenclature.objects.get(
                trackedmodel_ptr=comm.obj.pk,
            )
            commodity.indent = comm.indent
            commodity.parent_trackedmodel_ptr_id = parent_obj_pk
            commodity.save()
        except ReportGoodsNomenclature.DoesNotExist:
            pass


def save_commodities_parent(verbose=False):
    # Brute force approach to find the commodity parents.
    # CommodityTreeSnapshot creates the list of commodities and parent,
    # given a two number prefix.
    # Provide 99 prefix to be sure to cover all the possible
    # combination.
    # Once the tree is created, the parents are saved to
    # ReportGoodsNomenclature
    # In this way, Tomato code finds the correct information, without the need to
    # replicate it in sql

    moment = SnapshotMoment(transaction=None, date=date.today())
    start = time.time()
    for i in range(0, 100):
        prefix = f"{i:02d}"
        if verbose:
            print(f"Starting prefix {prefix}")
        commodities_collection = CommodityCollectionLoader(prefix=prefix).load(
            current_only=True,
            effective_only=True,
        )
        snapshot = CommodityTreeSnapshot(
            commodities=commodities_collection.commodities,
            moment=moment,
        )
        # snapshot = commodities_collection.get_snapshot(None, date.today())
        tree_edge_to_db(snapshot.edges)
    if verbose:
        print(f"Elapsed time {time.time() - start}")
