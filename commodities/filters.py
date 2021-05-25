from django.contrib.postgres.aggregates import StringAgg

from common.filters import TamatoFilterBackend


class GoodsNomenclatureFilterBackend(TamatoFilterBackend):
    search_fields = (
        StringAgg("item_id", delimiter=" "),
        StringAgg("descriptions__description", delimiter=" "),
    )  # XXX order is significant
