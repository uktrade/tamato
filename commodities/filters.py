from django.contrib.postgres.aggregates import StringAgg

from common.filters import TamatoFilterBackend


class GoodsNomenclatureFilterBackend(TamatoFilterBackend):
    search_fields = (
        "item_id",
        StringAgg("descriptions__description", delimiter=" "),
    )  # XXX order is significant

    def search_queryset(self, queryset, search_term):
        search_term = self.get_search_term(search_term)
        if search_term.isnumeric():
            return queryset.filter(item_id__startswith=search_term)

        return super().search_queryset(queryset, search_term)
