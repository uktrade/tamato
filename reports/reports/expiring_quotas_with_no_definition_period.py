import datetime
from django.db.models import Q
from reports.reports.base_table import ReportBaseTable
from quotas.models import (
    QuotaOrderNumber,
    QuotaDefinition,
    QuotaBlocking,
    QuotaSuspension,
)


class Report(ReportBaseTable):
    name = "Quotas Expiring Soon"
    enabled = True
    description = "Quotas with definition, sub-quota, blocking or suspension periods about to expire and no future definition period."
    tabular_reports = True
    tab_name = "Definitions"
    tab_name2 = "Sub-quota associations"
    tab_name3 = "Blocking periods"
    tab_name4 = "Suspension periods"
    current_time = datetime.datetime.now()
    future_time = current_time + datetime.timedelta(weeks=5)

    def headers(self) -> [dict]:
        return [
            {"text": "Quota Order Number"},
            {"text": "Definition Start Date"},
            {"text": "Definition End Date"},
        ]

    def row(self, row) -> [dict]:
        return [
            {"text": row.order_number},
            {"text": row.valid_between.lower},
            {"text": row.valid_between.upper},
        ]

    def rows(self) -> [[dict]]:
        table_rows = [self.row(row) for row in self.query()]

        if not any(table_rows):
            return [
                [{"text": "There is no data for this report at present"}]
                + [{"text": " "} for _ in range(len(self.headers()) - 1)]
            ]

        return table_rows

    def query(self):
        expiring_quotas = self.find_quota_definitions_expiring_soon()
        quotas_without_future_definition = self.find_quotas_without_future_definition(
            expiring_quotas
        )
        return quotas_without_future_definition

    def find_quota_definitions_expiring_soon(self):
        expiring_quotas = QuotaDefinition.objects.latest_approved().filter(
            Q(
                valid_between__isnull=False,
                valid_between__endswith__lte=self.future_time,
            )
            & Q(valid_between__endswith__gte=self.current_time)
            | Q(valid_between__endswith=None)
        )

        # Filter out quota definitions with associated future definitions
        filtered_quotas = []
        for quota in expiring_quotas:
            future_definitions = QuotaDefinition.objects.latest_approved().filter(
                order_number__order_number=quota.order_number,
                valid_between__startswith__gt=quota.valid_between.upper,
            )

            if not future_definitions.exists():
                filtered_quotas.append(quota)

        return filtered_quotas

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
            {"text": "Quota Order Number"},
            {"text": "Sub-quota associations SID"},
            {"text": "Sub-quota associations Start Date"},
            {"text": "Sub-quota associations End Date"},
            {"text": "Definition Period SID"},
        ]

    def row2(self, row) -> [dict]:
        sub_quotas_array = []

        for sub_quotas in row.sub_quotas.all():
            sub_quotas_array.append(
                {"text": row.order_number},
                {"text": sub_quotas.sid},
                {"text": sub_quotas.valid_between.lower},
                {"text": sub_quotas.valid_between.upper},
                {"text": row.sid},
            )

        return sub_quotas_array

    def rows2(self) -> [[dict]]:
        table_rows = [self.row2(row) for row in self.query()]

        if not any(table_rows):
            return [
                [{"text": "There is no data for this report at present"}]
                + [{"text": " "} for _ in range(len(self.headers2()) - 1)]
            ]

        return table_rows

    def find_quota_blocking_without_future_definition(self, expiring_quotas):
        matching_data = set()

        for quota_definition in expiring_quotas:
            associated_blocking_definitions = (
                QuotaBlocking.objects.latest_approved().filter(
                    quota_definition=quota_definition,
                )
            )

            if associated_blocking_definitions.exists():
                quota_definition.definition_start_date = (
                    quota_definition.valid_between.lower
                )
                quota_definition.definition_end_date = (
                    quota_definition.valid_between.upper
                )
                matching_data.add(quota_definition)

        return list(matching_data)

    def headers3(self) -> [dict]:
        return [
            {"text": "Quota Order Number"},
            {"text": "Blocking Period SIDs"},
            {"text": "Blocking Period Start Date"},
            {"text": "Blocking Period End Date"},
            {"text": "Definition Period SID"},
        ]

    def row3(self, row) -> [dict]:
        return [
            {"text": row.order_number},
            {"text": blocking.sid for blocking in row.quotablocking_set.all()},
            {
                "text": blocking.valid_between.lower
                for blocking in row.quotablocking_set.all()
            },
            {
                "text": blocking.valid_between.upper
                for blocking in row.quotablocking_set.all()
            },
            {"text": row.sid},
        ]

    def rows3(self) -> [[dict]]:
        table_rows = [self.row3(row) for row in self.query3()]

        if not any(table_rows):
            return [
                [{"text": "There is no data for this report at present"}]
                + [{"text": " "} for _ in range(len(self.headers3()) - 1)]
            ]

        return table_rows

    def query3(self):
        expiring_quotas = self.find_quota_definitions_expiring_soon()
        quota_blocking_without_future_definition = (
            self.find_quota_blocking_without_future_definition(expiring_quotas)
        )
        return quota_blocking_without_future_definition

    def find_quota_suspension_without_future_definition(self, expiring_quotas):
        matching_data = set()

        for quota_definition in expiring_quotas:
            future_definitions = QuotaSuspension.objects.latest_approved().filter(
                quota_definition=quota_definition,
            )

            if future_definitions.exists():
                quota_definition.definition_start_date = (
                    quota_definition.valid_between.lower
                )
                quota_definition.definition_end_date = (
                    quota_definition.valid_between.upper
                )
                matching_data.add(quota_definition)

        return list(matching_data)

    def headers4(self) -> [dict]:
        return [
            {"text": "Quota Order Number"},
            {"text": "Suspension Period SIDs"},
            {"text": "Suspension Period Start Date"},
            {"text": "Suspension Period End Date"},
            {"text": "Definition Period SID"},
        ]

    def row4(self, row) -> [dict]:
        return [
            {"text": row.order_number},
            {"text": suspension.sid for suspension in row.quotasuspension_set.all()},
            {
                "text": suspension.valid_between.lower
                for suspension in row.quotasuspension_set.all()
            },
            {
                "text": suspension.valid_between.upper
                for suspension in row.quotasuspension_set.all()
            },
            {"text": row.sid},
        ]

    def rows4(self) -> [[dict]]:
        table_rows = [self.row4(row) for row in self.query4()]

        if not any(table_rows):
            return [
                [{"text": "There is no data for this report at present"}]
                + [{"text": " "} for _ in range(len(self.headers4()) - 1)]
            ]

        return table_rows

    def query4(self):
        expiring_quotas = self.find_quota_definitions_expiring_soon()
        quota_suspension_without_future_definition = (
            self.find_quota_suspension_without_future_definition(expiring_quotas)
        )

        return quota_suspension_without_future_definition
