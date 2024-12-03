from datetime import date
from datetime import datetime
from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils.timezone import make_aware

from reports.reports.base_chart import ReportBaseChart
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus


class Report(ReportBaseChart):
    name = "CDS approvals in the last 12 months"
    description = "This chart shows the number of approved (published) workbaskets per day in the last 12 months."
    chart_type = "line"
    report_template = "chart_timescale"
    days_in_past = 365
    hover_text = "approved"

    def min_date_str(self):
        return str(date.today() + timedelta(days=-(self.days_in_past + 1)))

    def max_date_str(self):
        return str(date.today())

    def data(self):
        result = []

        for row in self.query():
            result.append({"y": row["count"], "x": str(row["date"])})

        return result

    def labels(self):
        return []

    def query(self):
        return (
            WorkBasket.objects.filter(
                updated_at__gt=make_aware(
                    datetime.today() + timedelta(days=-(self.days_in_past + 1)),
                ),
                status=WorkflowStatus.PUBLISHED,
            )
            .values(date=TruncDate("updated_at"))
            .annotate(count=Count("id"))
            .order_by("date")
        )
