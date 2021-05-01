from common.models.mixins.validity import ValidityStartQueryset
from common.models.records import TrackedModelQuerySet


class GoodsNomenclatureIndentQuerySet(ValidityStartQueryset, TrackedModelQuerySet):
    pass
