import datetime

from django.db.models import Max

from open_data.models import ReportDateStamp
from open_data.models.datestamp import EventChoice


def get_report_timestamp() -> datetime.datetime:
    return ReportDateStamp.objects.filter(
        event=EventChoice.REFRESH_OPEN_DATA,
    ).aggregate(Max("event_date"))["event_date__max"]


def get_report_timestamp_str() -> str:
    report_date_stamp = get_report_timestamp()
    if report_date_stamp:
        return f'Report correct up to {report_date_stamp.strftime("%X %x")}'
    else:
        report_date_str = "Report time stamp missing."
    return report_date_str
