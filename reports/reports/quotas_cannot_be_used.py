import datetime

from reports.reports.base_table import ReportBaseTable

from quotas.models import QuotaOrderNumber, QuotaDefinition, QuotaOrderNumberOriginExclusion, QuotaOrderNumberOrigin
from measures.models import Measure, MeasureExcludedGeographicalArea

from django.db.models import OuterRef, Subquery, Exists

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
        quotas_can_be_used = self.find_quotas_that_cannot_be_used(quotas_with_definition_periods)
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
    #             exclusions = MeasureExcludedGeographicalArea.objects.latest_approved().filter(modified_measure=measure)
    #             # exclusions = measure.exclusions.approved_up_to_transaction(transaction)
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

    # def find_quotas_that_cannot_be_used(self, quotas_with_definition_periods):
    #     matching_exclusion_data = set()
    #     matching_data = set()
    #     not_matching_exclusion_data = set()
    #
    #     for quota in quotas_with_definition_periods:
    #         measures = Measure.objects.latest_approved().filter(order_number=quota.order_number)
    #         quota_order_number = QuotaOrderNumber.objects.latest_approved().filter(
    #             order_number=quota.order_number).order_by("-sid").first()
    #         quota_order_number_origin = QuotaOrderNumberOrigin.objects.latest_approved().filter(
    #             order_number_id=quota_order_number.pk)
    #
    #         for origin in quota_order_number_origin:
    #             geo_exclusions = QuotaOrderNumberOriginExclusion.objects.latest_approved().filter(
    #                 origin_id=origin.pk
    #             )
    #
    #             for geo_exclusion in geo_exclusions:
    #                 for measure in measures:
    #                     # transaction = measure.transaction
    #                     # exclusions = measure.exclusions.approved_up_to_transaction(transaction)
    #                     exclusions = MeasureExcludedGeographicalArea.objects.latest_approved().filter(modified_measure=measure)
    #                     for exclusion in exclusions:
    #                         if exclusion.excluded_geographical_area is not None and geo_exclusion.excluded_geographical_area is not None:
    #                             if exclusion.excluded_geographical_area == geo_exclusion.excluded_geographical_area and quota.order_number not in matching_exclusion_data:
    #                                 if quota not in matching_exclusion_data:
    #                                     print(quota)
    #                                     matching_exclusion_data.add(quota)
    #
    #         if quota not in matching_exclusion_data:
    #             not_matching_exclusion_data.add(quota)
    #
    #     current_time = datetime.datetime.now()
    #     quota_order_numbers_without_definitions = QuotaOrderNumber.objects.latest_approved().filter(
    #         valid_between__isnull=False,
    #         valid_between__startswith__lt=current_time,
    #         valid_between__endswith__gte=current_time
    #     ).exclude(definitions__in=quotas_with_definition_periods)
    #
    #     for quota in quota_order_numbers_without_definitions:
    #         matching_data.add(quota)
    #
    #     for quota in not_matching_exclusion_data:
    #         matching_data.add(quota)
    #
    #     for quota in matching_data:
    #         if quota in not_matching_exclusion_data:
    #             quota.reason = 'Geographical area/exclusions data does not have any measures with matching data'
    #         else:
    #             quota.reason = 'Definition period has not been set'
    #
    #     return list(matching_data)

    def find_quotas_that_cannot_be_used(self, quotas_with_definition_periods):
        matching_data = set()

        current_time = datetime.datetime.now()

        quota_order_numbers_without_definitions = QuotaOrderNumber.objects.latest_approved().filter(
            valid_between__isnull=False,
            valid_between__startswith__lt=current_time,
            valid_between__endswith__gte=current_time
        ).exclude(definitions__in=quotas_with_definition_periods)

        for quota in quotas_with_definition_periods:
            measures = Measure.objects.latest_approved().filter(order_number=quota.order_number)

            if not Exists(measures.filter(order_number=quota.order_number)):
                matching_data.add(quota)
            else:
                quota_order_number = QuotaOrderNumber.objects.latest_approved().filter(
                    order_number=quota.order_number
                ).order_by("-sid").first()

                if quota_order_number:
                    quota_order_number_origin = QuotaOrderNumberOrigin.objects.latest_approved().filter(
                        order_number_id=quota_order_number.pk
                    )

                    for origin in quota_order_number_origin:
                        geo_exclusions = QuotaOrderNumberOriginExclusion.objects.latest_approved().filter(
                            origin_id=origin.pk
                        )

                        for geo_exclusion in geo_exclusions:
                            exclusions = MeasureExcludedGeographicalArea.objects.latest_approved().filter(
                                modified_measure__order_number=quota.order_number,
                                excluded_geographical_area=geo_exclusion.excluded_geographical_area
                            )

                            if exclusions.exists():
                                matching_data.discard(quota)
                                break

        matching_data.update(quota_order_numbers_without_definitions)

        for quota in matching_data:
            if quota not in quotas_with_definition_periods:
                quota.reason = 'Definition period has not been set'
            else:
                quota.reason = 'Geographical area/exclusions data does not have any measures with matching data'

        return list(matching_data)

