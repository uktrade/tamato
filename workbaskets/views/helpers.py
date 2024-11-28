from commodities.models.orm import GoodsNomenclature
from commodities.models.orm import GoodsNomenclatureIndent


def get_comm_codes_affected_by_workbasket_changes(workbasket):
    comm_codes = {
        item.pk
        for item in workbasket.tracked_models.all()
        if isinstance(item, GoodsNomenclature)
    }
    indented_goods_nom = {
        item.indented_goods_nomenclature.pk
        for item in workbasket.tracked_models.all()
        if isinstance(item, GoodsNomenclatureIndent)
    }

    return list(comm_codes.union(indented_goods_nom))
