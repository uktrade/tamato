from commodities.models.dc import CommodityCollectionLoader
from commodities.models.dc import CommodityTreeSnapshot
from commodities.models.dc import SnapshotMoment
from geo_areas.models import GeographicalArea
from measures.models import MeasureType
from measures.snapshots import MeasureSnapshot


def get_measures_on_declarable_commodities(transaction, item_id, date=None):
    """Uses CommodityTreeSnapshot and MeasureSnapshot to look up the commodity
    tree to find measures defined on parent commodities that therefore also
    apply to the given child commodity."""
    prefix = item_id[0:2]
    commodities_collection = CommodityCollectionLoader(prefix=prefix).load()

    moment = SnapshotMoment(transaction=transaction, date=date)
    tree = CommodityTreeSnapshot(
        commodities=commodities_collection.commodities,
        moment=moment,
    )
    this_commodity = list(
        filter(lambda c: c.item_id == item_id, tree.commodities),
    )[0]
    measure_snapshot = MeasureSnapshot(moment, tree)
    return measure_snapshot.get_applicable_measures(this_commodity)


def get_comm_code_measure_type_103(comm_codes, date=None):
    output = []
    third_country_duty = MeasureType.objects.get(sid=103)

    for code in comm_codes:
        if code.item_id.startswith("99") or code.item_id.startswith("98"):
            continue
        measures = get_measures_on_declarable_commodities(
            code.transaction,
            code.item_id,
            date,
        )
        if not measures:
            item = (code, None)
        else:
            item = (
                code,
                measures.filter(
                    measure_type=third_country_duty,
                    geographical_area=GeographicalArea.objects.erga_omnes().first(),
                ),
            )
        output.append(item)
    return output
