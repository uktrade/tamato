from django.db import models
from django.db.models import TextChoices

from open_data.models.utils import create_open_data_name


class EventChoice(TextChoices):
    """Code which indicates the event in the datestamp table."""

    REFRESH_OPEN_DATA = "Refresh", "Refresh open data"
    EXPORT_OPEN_DATA = "Export", "Export open data"


class OriginChoice(TextChoices):
    """Code which indicates the origin event in the datestamp table."""

    MANAGEMENT_COMMAND = "Command", "Management command"
    CELERY_WORKER = "" "", "Async process"
    TEST = 2, "Test"


class ReportDateStamp(models.Model):
    """
    The table will have a maximum of two entries, one for the data refresh and
    one for the data export.

    Useful to decide if the data available is the latest or not More information
    about the data refresh are stored in the log
    """

    event = models.CharField(choices=EventChoice.choices, max_length=50)
    event_date = models.DateTimeField(auto_now_add=True, editable=False, null=True)
    origin = models.CharField(choices=OriginChoice.choices, max_length=50)

    class Meta:
        db_table = create_open_data_name("datestamp")
