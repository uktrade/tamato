from datetime import date
from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import TruncDate

from reports.reports.base_chart import ReportBaseChart
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus


class Report(ReportBaseChart):
    name = "CDS rejections in the last 12 months"
    description = (
        "This report shows the count of rejected (errored) workbaskets in the last 12 months per day. "
        "<br><br>"
        "Note: workbaskets that are rejected, tend to be removed, so this report is for demonstration "
        "purposes only at this point. there remains some work to do to confidently track and collect "
        "rejection information in TAP suitable for reporting purposes."
    )
    chart_type = "line"
    report_template = "chart_timescale"
    days_in_past = 120
    hover_text = "rejected"

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
                updated_at__gt=date.today() + timedelta(days=-(self.days_in_past + 1)),
                status=WorkflowStatus.ERRORED,
            )
            .values(date=TruncDate("updated_at"))
            .annotate(count=Count("id"))
            .order_by("date")
        )
