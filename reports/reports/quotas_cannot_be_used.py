import datetime

from reports.reports.base_table import ReportBaseTable

from quotas.models import QuotaOrderNumber, QuotaDefinition
from measures.models import Measure


class Report(ReportBaseTable):
    name = "Quotas Missing Data"
    enabled = True

    def headers(self) -> [dict]:
        return [
            {"text": "Order number"},
            {"text": "start date"},
            {"text": "end date"},
        ]

    def row(self, row: QuotaDefinition) -> [dict]:
        return [
            {"text": row.order_number},
            {"text": row.valid_between.lower},
            {"text": row.valid_between.upper},
            {"text": row.reason}
        ]

    def rows(self) -> [[dict]]:
        table_rows = []
        for row in self.query():
            table_rows.append(self.row(row))

        return table_rows

    def query(self):
        quotas_with_definition_periods = self.get_quotas_with_definition_periods()
        quotas_can_be_used = self.find_quotas_that_can_be_used(quotas_with_definition_periods)
        return quotas_can_be_used

    def get_quotas_with_definition_periods(self):
        quota_definitions = QuotaDefinition.objects.latest_approved().filter(
            valid_between__isnull=False,
            valid_between__startswith__lt=datetime.datetime.now(),
            valid_between__endswith__gte=datetime.datetime.now(),
            )

        return quota_definitions

    # def find_quotas_that_can_be_used(self, quotas_with_definition_periods):
    #     # Quota definition periods that have measures in place which match
    #     matching_exclusion_data = []
    #     matching_data = []
    #     for quota in quotas_with_definition_periods:
    #         measures = Measure.objects.latest_approved().filter(order_number=quota.order_number)
    #         for measure in measures:
    #             transaction = measure.transaction
    #             exclusions = measure.exclusions.approved_up_to_transaction(transaction)
    #
    #             for exclusion in exclusions:
    #                 geo_area = exclusion.excluded_geographical_area
    #                 quota_geographical_exclusions_data = QuotaOrderNumber.objects.latest_approved().filter(
    #                     order_number=quota.order_number)
    #
    #                 for quota_exclusions_query in quota_geographical_exclusions_data:
    #                     for geographical_exclusions in quota_exclusions_query.geographical_exclusions:
    #                         if geographical_exclusions == geo_area and quota.order_number not in matching_exclusion_data:
    #                             matching_exclusion_data.append(quota)
    #
    #         if quota not in matching_data:
    #             quota.reason = 'Geographical area/exclusions data does not have any measures with matching data'
    #             matching_data.append(quota)
    #
    #     quota_order_numbers_without_definitions = QuotaOrderNumber.objects.latest_approved().filter(
    #         valid_between__isnull=False,
    #         valid_between__startswith__lt=datetime.datetime.now(),
    #         valid_between__endswith__gte=datetime.datetime.now()).exclude(
    #         definitions__in=quotas_with_definition_periods
    #     )
    #
    #     for quota in quota_order_numbers_without_definitions:
    #         if quota not in matching_data:
    #             quota.reason = 'Definition period has not been set'
    #             matching_data.append(quota)
    #
    #     return matching_data

    def find_quotas_that_can_be_used(self, quotas_with_definition_periods):
        matching_exclusion_data = set()
        matching_data = set()
        excluded_geo_areas = set()

        for quota in quotas_with_definition_periods:
            measures = Measure.objects.latest_approved().filter(order_number=quota.order_number)
            for measure in measures:
                transaction = measure.transaction
                exclusions = measure.exclusions.approved_up_to_transaction(transaction)

                for exclusion in exclusions:
                    geo_area = exclusion.excluded_geographical_area
                    excluded_geo_areas.add(geo_area)

            if not excluded_geo_areas:
                matching_exclusion_data.add(quota)

        current_time = datetime.datetime.now()
        quota_order_numbers_without_definitions = QuotaOrderNumber.objects.latest_approved().filter(
            valid_between__isnull=False,
            valid_between__startswith__lt=current_time,
            valid_between__endswith__gte=current_time
        ).exclude(definitions__in=quotas_with_definition_periods)

        for quota in quota_order_numbers_without_definitions:
            matching_data.add(quota)

        for quota in matching_exclusion_data:
            matching_data.add(quota)

        for quota in matching_data:
            if quota in matching_exclusion_data:
                quota.reason = 'Geographical area/exclusions data does not have any measures with matching data'
            else:
                quota.reason = 'Definition period has not been set'

        return list(matching_data)
