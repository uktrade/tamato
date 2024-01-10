import datetime
from django.db.models import Exists, Q
from reports.reports.base_table import ReportBaseTable
from quotas.models import (
    QuotaOrderNumber,
    QuotaDefinition,
    QuotaOrderNumberOriginExclusion,
    QuotaOrderNumberOrigin,
)
from measures.models import Measure, MeasureExcludedGeographicalArea

class Report(ReportBaseTable):
    name = "Quotas Expiring Soon"
    enabled = True
    description = "Quotas with definition periods about to expire and no future definition period"

    def headers(self) -> [dict]:
        return [
            {"text": "Quota Order Number"},
            {"text": "Definition Start Date"},
            {"text": "Definition End Date"},
            {"text": "Reason"},
        ]

    def row(self, row: QuotaDefinition) -> [dict]:
        return [
            {"text": row.order_number},
            {"text": row.definition_start_date},
            {"text": row.definition_end_date},
            {"text": row.reason},
        ]

    def rows(self) -> [[dict]]:
        table_rows = []
        for row in self.query():
            table_rows.append(self.row(row))

        return table_rows

    def query(self):
        expiring_quotas = self.find_quotas_expiring_soon()
        quotas_without_future_definition = self.find_quotas_without_future_definition(
            expiring_quotas
        )
        return quotas_without_future_definition

    def find_quotas_expiring_soon(self):
        current_time = datetime.datetime.now()
        future_time = current_time + datetime.timedelta(weeks=5)

        filter_query = (
            Q(valid_between__endswith__gte=current_time)
            | Q(valid_between__endswith=None)
        ) & Q(
            valid_between__isnull=False,
            valid_between__endswith__lte=future_time,
        )

        quotas_expiring_soon = QuotaDefinition.objects.latest_approved().filter(
            filter_query
        )

        return list(quotas_expiring_soon)


    def find_quotas_without_future_definition(self, expiring_quotas):
        matching_data = set()

        for quota in expiring_quotas:
            future_definitions = QuotaDefinition.objects.latest_approved().filter(
                order_number=quota.order_number,
                valid_between__startswith__gt=quota.valid_between.upper,
            )

            if not future_definitions.exists():
                matching_data.add(quota)

        for quota in matching_data:
            quota.definition_start_date = quota.valid_between.lower
            quota.definition_end_date = quota.valid_between.upper
            quota.reason = "Definition period about to expire with no future definition period"

        return list(matching_data)
