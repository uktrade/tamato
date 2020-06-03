from django.db import models


class WorkBasket(models.Model):
    name = models.CharField(max_length=24)
