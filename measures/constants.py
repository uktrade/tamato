from django.db import models

START = "start"
GEOGRAPHICAL_AREA_EXCLUSIONS = "geographical_area_exclusions"


class MeasureEditSteps(models.TextChoices):
    START_DATE = ("start_date", "Start date")
    END_DATE = ("end_date", "End date")
    QUOTA_ORDER_NUMBER = ("quota_order_number", "Quota order number")
    REGULATION = ("regulation", "Regulation")
    DUTIES = ("duties", "Duties")
    GEOGRAPHICAL_AREA_EXCLUSIONS = (
        "geographical_area_exclusions",
        "Geographical area exclusions",
    )
