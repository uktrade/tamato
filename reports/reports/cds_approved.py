from datetime import date
from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import TruncDate

from reports.reports.base_chart import ReportBaseChart
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus


class Report(ReportBaseChart):
    name = "CDS approvals in this quarter"
    chart_type = "line"
    report_template = "chart_timescale"
    days_in_past = 50
    hover_text = "approved"

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
                updated_at__gt=date.today() + timedelta(days=-(self.days_in_past + 1)),
                status=WorkflowStatus.PUBLISHED,
            )
            .values(date=TruncDate("updated_at"))
            .annotate(count=Count("id"))
            .order_by("date")
        )
