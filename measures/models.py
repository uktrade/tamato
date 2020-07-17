from django.db import models

from commodities.models import GoodsNomenclature
from common.models import TrackedModel, ValidityMixin


class Measure(TrackedModel, ValidityMixin):
    commodity_code = models.ForeignKey(
        GoodsNomenclature, on_delete=models.PROTECT, related_name="measures"
    )
    duty = models.CharField(max_length=512)
