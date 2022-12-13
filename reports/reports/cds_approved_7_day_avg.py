from datetime import date
from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import TruncDate

from reports.reports.base_chart import ReportBaseChart
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus


class Report(ReportBaseChart):
    name = "CDS approvals (7 day average) in the last 12 months"
    description = (
        "This report shows the 7 day average of approved (published) "
        "workbaskets in the last 12 months per day"
    )
    chart_type = "line"
    report_template = "chart_timescale"
    days_in_past = 365
    hover_text = "7 day average"

    def min_date_str(self):
        return str(date.today() + timedelta(days=-(self.days_in_past + 1)))

    def max_date_str(self):
        return str(date.today())

    def data(self):
        result = []

        for row in self.query():
            data = self.query().filter(
                date__range=(
                    row["date"] - timedelta(days=7),
                    row["date"],
                ),
            )
            result.append(
                {
                    "y_count": row["count"],
                    "x": str(row["date"]),
                    "y": self.calculate_7da(data),
                },
            )

        # Populate unpopulated dates in range
        for days_ago in range(365):
            check_date = date.today() - timedelta(days=days_ago)
            if not self.entry_for_date_exists(
                date.today() - timedelta(days=days_ago),
                result,
            ):
                data = self.query().filter(
                    date__range=(
                        check_date - timedelta(days=7),
                        check_date,
                    ),
                )
                # add it
                result.append(
                    {
                        "y_count": 0,
                        "x": str(check_date),
                        "y": self.calculate_7da(data),
                    },
                )

        return result

    def entry_for_date_exists(self, target_date, results):
        exists = False

        for row in results:
            if row["x"] == str(target_date):
                exists = True
                break

        return exists

    def calculate_7da(self, data):
        total = 0

        for row in data:
            total += row["count"]

        if total == 0:
            return 0

        return total / 7

    def labels(self):
        return []

    def query(self):
        return (
            WorkBasket.objects.filter(
                updated_at__gt=date.today() + timedelta(days=-(self.days_in_past + 8)),
                status=WorkflowStatus.PUBLISHED,
            )
            .values(date=TruncDate("updated_at"))
            .annotate(count=Count("id"))
            .order_by("date")
        )
