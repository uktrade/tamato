from commodities.models.orm import GoodsNomenclature
from commodities.models.orm import GoodsNomenclatureIndent
from workbaskets.models import MissingMeasureCommCode


def get_comm_codes_affected_by_workbasket_changes(workbasket):
    comm_codes = {
        item
        for item in workbasket.tracked_models.all()
        if isinstance(item, GoodsNomenclature)
    }
    indented_goods_nom = {
        item.indented_goods_nomenclature
        for item in workbasket.tracked_models.all()
        if isinstance(item, GoodsNomenclatureIndent)
    }

    # delete any previous checks on workbasket first
    MissingMeasureCommCode.objects.filter(workbasket=workbasket).delete()

    return comm_codes.union(indented_goods_nom)
