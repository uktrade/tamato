from django.db import models

START = "start"


class MeasureEditSteps(models.TextChoices):
    END_DATE = ("end_dates", "End date")
    START_DATE = ("start_date", "Start date")
