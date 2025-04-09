import datetime

from django.db.models import Max

from open_data.models import ReportDateStamp
from open_data.models.datestamp import EventChoice


def get_report_data() -> datetime.datetime:
    return ReportDateStamp.objects.filter(
        event=EventChoice.REFRESH_OPEN_DATA,
    ).aggregate(Max("event_date"))["event_date__max"]
