import datetime
from django.db.models import Q
from reports.reports.base_table import ReportBaseTable
from quotas.models import (
    QuotaOrderNumber,
    QuotaDefinition,
)


class Report(ReportBaseTable):
    name = "Quotas Expiring Soon"
    enabled = True
    description = (
        "Quotas with definition periods about to expire and no future definition period"
    )
    tabular_reports = True
    tab_name = "Definitions"
    tab_name2 = "Sub-quota associations"
    tab_name3 = "Blocking periods"
    tab_name4 = "Suspension periods"

    def headers(self) -> [dict]:
        return [
            {"text": "Quota Order Number"},
            {"text": "Definition Start Date"},
            {"text": "Definition End Date"},
        ]

    def row(self, row: QuotaDefinition) -> [dict]:
        return [
            {"text": row.order_number},
            {"text": row.valid_between.lower},
            {"text": row.valid_between.upper},
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

        filter_query = Q(
            valid_between__isnull=False,
            valid_between__endswith__lte=future_time,
        ) & Q(valid_between__endswith__gte=current_time) | Q(valid_between__endswith=None)
        

        quotas_expiring_soon = QuotaDefinition.objects.latest_approved().filter(
            filter_query
        )
        print(quotas_expiring_soon.filter(sid=23816))

        return list(quotas_expiring_soon)

    def find_quotas_without_future_definition(self, expiring_quotas):
        matching_data = set()

        for quota in expiring_quotas:
            future_definitions = QuotaOrderNumber.objects.latest_approved().filter(
                order_number=quota.order_number,
                valid_between__startswith__gt=quota.valid_between.upper,
            )

            if not future_definitions.exists():
                quota.definition_start_date = quota.valid_between.lower
                quota.definition_end_date = quota.valid_between.upper
                matching_data.add(quota)


        return list(matching_data)

    def headers2(self) -> [dict]:
        return [
            {"text": "1234"},
            {"text": "Definition Start Date"},
            {"text": "Definition End Date"},
        ]

    def row2(self, row: QuotaDefinition) -> [dict]:
        return [
            {"text": row.order_number},
            {"text": row.valid_between.lower},
            {"text": row.valid_between.upper},
        ]

    def rows2(self) -> [[dict]]:
        table_rows = []
        for row in self.query():
            table_rows.append(self.row(row))

        return table_rows

    def query2(self):
        expiring_quotas = self.find_quotas_expiring_soon()
        quotas_without_future_definition = self.find_quotas_without_future_definition(
            expiring_quotas
        )
        return quotas_without_future_definition
    
    def headers3(self) -> [dict]:
        return [
            {"text": "1234"},
            {"text": "Definition Start Date"},
            {"text": "Definition End Date"},
        ]

    def row3(self, row: QuotaDefinition) -> [dict]:
        return [
            {"text": row.order_number},
            {"text": row.valid_between.lower},
            {"text": row.valid_between.upper},
        ]

    def rows3(self) -> [[dict]]:
        table_rows = []
        for row in self.query():
            table_rows.append(self.row(row))

        return table_rows

    def query3(self):
        expiring_quotas = self.find_quotas_expiring_soon()
        quotas_without_future_definition = self.find_quotas_without_future_definition(
            expiring_quotas
        )
        return quotas_without_future_definition
    
    def headers4(self) -> [dict]:
        return [
            {"text": "1234"},
            {"text": "Definition Start Date"},
            {"text": "Definition End Date"},
        ]

    def row4(self, row: QuotaDefinition) -> [dict]:
        return [
            {"text": row.order_number},
            {"text": row.valid_between.lower},
            {"text": row.valid_between.upper},
        ]

    def rows4(self) -> [[dict]]:
        table_rows = []
        for row in self.query():
            table_rows.append(self.row(row))

        return table_rows

    def query4(self):
        expiring_quotas = self.find_quotas_expiring_soon()
        quotas_without_future_definition = self.find_quotas_without_future_definition(
            expiring_quotas
        )
        return quotas_without_future_definition