from django.db import models

from commodities.models import Commodity


class Measure(models.Model):
    commodity = models.ForeignKey(Commodity, on_delete=models.PROTECT, related_name='measures')
    duty = models.CharField(max_length=512)
