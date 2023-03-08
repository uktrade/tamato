from django.db import models

START = "start"


class MeasureEditSteps(models.TextChoices):
    START_DATE = ("start_date", "Start date")
    END_DATE = ("end_date", "End date")
    QUOTA_ORDER_NUMBER = ("quota_order_number", "Quota order number")
    REGULATION = ("regulation", "Regulation")
