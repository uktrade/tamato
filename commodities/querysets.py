from common.models.mixins.validity import ValidityStartQueryset
from common.models.tracked_qs import TrackedModelQuerySet


class GoodsNomenclatureIndentQuerySet(ValidityStartQueryset, TrackedModelQuerySet):
    pass
