from django.db import models

START = "start"


class MeasureEditSteps(models.TextChoices):
    START_DATE = ("start_date", "Start date")
    END_DATE = ("end_dates", "End date")
