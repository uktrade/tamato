from django.db import models

START = "start"


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


MEASURE_CONDITIONS_FORMSET_PREFIX = "measure-conditions-formset"
MEASURE_COMMODITIES_FORMSET_PREFIX = "measure_commodities_duties_formset"
