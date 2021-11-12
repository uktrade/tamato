from common.models.mixins.validity import ValidityStartQueryset
from common.models.trackedmodel_queryset import TrackedModelQuerySet


class GoodsNomenclatureIndentQuerySet(ValidityStartQueryset, TrackedModelQuerySet):
    pass
