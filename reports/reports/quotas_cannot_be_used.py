import datetime
from datetime import date
from datetime import timedelta

from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.core.exceptions import ObjectDoesNotExist

from reports.reports.base_table import ReportBaseTable

from quotas.models import QuotaOrderNumber, QuotaDefinition, QuotaOrderNumberOriginExclusion
from measures.models import Measure, MeasureExcludedGeographicalArea

from collections import defaultdict


# Third attempt - Ensure everything is cached.. hopefully speeds it up!
from collections import defaultdict

class Report(ReportBaseTable):
    name = "Quotas Missing Data"
    enabled = True

    def headers(self) -> [dict]:
        return [
            {"text": "order number"},
            {"text": "start date"},
            {"text": "end date"},
        ]

    def row(self, row: Measure) -> [dict]:
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
        quotas_with_definition_periods = self.get_quotas_with_definition_periods()
        quotas_can_be_used = self.find_quotas_that_can_be_used(quotas_with_definition_periods)
        return quotas_can_be_used

    def get_quotas_with_definition_periods(self):
        quota_definitions = QuotaDefinition.objects.latest_approved().filter(valid_between__isnull=False,
                                                                             valid_between__startswith__lt=datetime.datetime.now(),
                                                                             valid_between__endswith__gte=datetime.datetime.now(),
                                                                             )

        return quota_definitions

    def find_quotas_that_can_be_used(self, quotas_with_definition_periods):
        quotas_can_be_used = []

        # measure_cache = defaultdict(list)
        excluded_geo_area_cache = defaultdict(dict)
        quotas = [quota.order_number for quota in quotas_with_definition_periods]

        quota_definitions = []
        check_quota_measures = []

        for quota_number in quotas:
            if quota_number.valid_between.upper is not None:
                quotas_can_be_used = (Q(
                        order_number=quota_number.order_number,
                        valid_between__startswith__lt=quota_number.valid_between.lower,
                    ) & (
                        Q(valid_between__endswith__gte=quota_number.valid_between.upper)

                    ))

                if Measure.objects.latest_approved().filter(quotas_can_be_used):
                    check_quota_measures.append(quota_number)

            else:
                quotas_cant_be_used = (
                    Q(
                        order_number=quota_number.order_number,
                        valid_between__startswith__lt=quota_number.valid_between.lower,
                    )
                )
                if Measure.objects.latest_approved().filter(quotas_cant_be_used):
                    if quota_number not in quota_definitions:
                        quota_definitions.append(quota_number)

            measure_queryset = Measure.objects.latest_approved().filter(order_number=quota_number).select_related(
                'transaction', 'order_number')

            for measure in measure_queryset.iterator():
                transaction = measure.transaction
                exclusions = measure.exclusions.approved_up_to_transaction(transaction)

                valid_between_upper = measure.valid_between.upper
                if valid_between_upper is not None:
                    member_exists_query = measure.geographical_area.members.filter(
                        Q(
                            member__area_id__in=[exclusion.excluded_geographical_area.area_id for exclusion in
                                                 exclusions],
                            valid_between__startswith__lte=measure.valid_between.lower
                        )
                        &
                        (
                                Q(valid_between__endswith__gte=valid_between_upper) |
                                Q(valid_between__endswith=None)
                        )
                    )

                    if member_exists_query.exists():
                        if quota_number not in quota_definitions:
                            quota_definitions.append(quota_number)

        return quota_definitions


        # quota_definitions = set()
        # cached_measures = {}  # Store cached measures by quota number
        #
        # for quota in quotas_with_definition_periods:
        #     if quota.valid_between.upper is not None:
        #         quotas_can_be_used = (
        #                 Q(
        #                     order_number=quota.order_number,
        #                     valid_between__startswith__lt=quota.valid_between.lower,
        #                 ) &
        #                 (
        #                     Q(valid_between__endswith__gte=quota.valid_between.upper)
        #                 )
        #         )
        #     else:
        #         quotas_cant_be_used = (
        #             Q(
        #                 order_number=quota.order_number,
        #                 valid_between__startswith__lt=quota.valid_between.lower,
        #             )
        #         )
        #
        #     # Check if cached measure exists for this quota, otherwise query the database
        #     if quota.order_number in cached_measures:
        #         measure_queryset = cached_measures[quota.order_number]
        #     else:
        #         measure_queryset = Measure.objects.latest_approved().filter(
        #             order_number=quota.order_number).select_related(
        #             'transaction', 'order_number')
        #         cached_measures[quota.order_number] = measure_queryset
        #
        #     if Measure.objects.latest_approved().filter(quotas_can_be_used).count() == 0:
        #         quota_definitions.add(quota.order_number)
        #
        #     for measure in measure_queryset.iterator():
        #         transaction = measure.transaction
        #         exclusions = measure.exclusions.approved_up_to_transaction(transaction)
        #
        #         valid_between_upper = measure.valid_between.upper
        #         if valid_between_upper is not None:
        #             member_exists_query = measure.geographical_area.members.filter(
        #                 Q(
        #                     member__area_id__in=[exclusion.excluded_geographical_area.area_id for exclusion in
        #                                          exclusions],
        #                     valid_between__startswith__lte=measure.valid_between.lower
        #                 )
        #                 &
        #                 (
        #                         Q(valid_between__endswith__gte=valid_between_upper) |
        #                         Q(valid_between__endswith=None)
        #                 )
        #             )
        #
        #             if member_exists_query.exists():
        #                 quota_definitions.add(quota.order_number)
        #
        # return list(quota_definitions)

# First attempt.. generally terrible code
# class Report(ReportBaseChart):
#     name = "Quotas missing data"
#     description = "This report shows the quotas that cannot be used by traders due to missing data"
#     # chart_type = "line"
#     report_template = "text"
#     # days_in_past = 365
#     hover_text = "approved"
#     quotas_that_can_be_used = []
#
#     # def min_date_str(self):
#     #     return str(date.today() + timedelta(days=-(self.days_in_past + 1)))
#     #
#     # def max_date_str(self):
#     #     return str(date.today())
#
#     def data(self):
#         result = []
#
#         for row in self.query():
#             result.append({"y": row["count"], "x": str(row["date"])})
#
#         return result
#
#     def labels(self):
#         return []
#
#     def query(self):
#         approved_quota_sids = [quota.sid for quota in
#                                QuotaOrderNumber.objects.latest_approved().all()]
#
#         quotas_with_definition_periods = []
#         for quota_sid in approved_quota_sids:
#             quota_definition = QuotaDefinition.objects.latest_approved().filter(sid=quota_sid)
#             if quota_definition.valid_between:
#                 quotas_with_definition_periods.append(quota_definition.sid)
#
#         for quota in quotas_with_definition_periods:
#             quotas = QuotaOrderNumber.objects.latest_approved().filter(sid=quota)
#
#             for quota_number in quotas:
#                 measures = Measure.objects.latest_approved().filter(order_number=quota_number)
#
#                 for measure in measures:
#                     measure_excluded_geo_area = MeasureExcludedGeographicalArea.current_objects.get(
#                         trackedmodel_ptr_id=measure.trackedmodel_ptr_id).excluded_geographical_area
#                     order_number_excluded_geo_area = QuotaOrderNumberOriginExclusion.objects.latest_approved().get(
#                         origin_id=quota_number.trackedmodel_ptr_id)
#                     if measure.geographical_area == quota_number.origins:
#                         if measure_excluded_geo_area == order_number_excluded_geo_area:
#                             self.quotas_that_can_be_used.append(quota_number.sid)
#
#         return self.quotas_that_can_be_used


# Second attempt - takes far too long to run
# class Report(ReportBaseChart):
#     name = "Quotas Missing Data"
#     description = "This report shows the quotas that cannot be used by traders due to missing data"
#     report_template = "text"
#     hover_text = "approved"
#     chart_type = "line"
#     days_in_past = 365
#
#     def data(self):
#         result = []
#
#         for row in self.query():
#             result.append({"y": row["count"], "x": str(row["date"])})
#
#         return result
#
#     def labels(self):
#         return []
#
#     def query(self):
#         approved_quota_sids = self.get_approved_quota_sids()
#
#         quotas_with_definition_periods = self.get_quotas_with_definition_periods(approved_quota_sids)
#
#         quotas_can_be_used = self.find_quotas_that_can_be_used(quotas_with_definition_periods)
#
#         return quotas_can_be_used
#
#     def get_approved_quota_sids(self):
#         return QuotaOrderNumber.objects.latest_approved().all()
#
#     def get_quotas_with_definition_periods(self, approved_quota_sids):
#         quotas_with_periods = []
#         for quota_number in approved_quota_sids:
#             quota_definition = QuotaDefinition.objects.latest_approved().filter(order_number=quota_number)
#             for quota in quota_definition:
#                 if quota.valid_between:
#                     quotas_with_periods.append(quota)
#         return quotas_with_periods
#
#     def find_quotas_that_can_be_used(self, quotas_with_definition_periods):
#         quotas_can_be_used = []
#
#         for quota in quotas_with_definition_periods:
#             quotas = QuotaOrderNumber.objects.latest_approved().filter(sid=quota.sid)
#
#             for quota_number in quotas:
#                 if self.can_quota_be_used(quota_number):
#                     quotas_can_be_used.append(quota_number.sid)
#
#         return quotas_can_be_used
#
#     def can_quota_be_used(self, quota_number):
#         measures = Measure.objects.latest_approved().filter(order_number=quota_number)
#
#         for measure in measures:
#             print('heloo')
#             print(measure.trackedmodel_ptr_id)
#             print('end')
#             try:
#                 measure_excluded_geo_area = MeasureExcludedGeographicalArea.current_objects.get(
#                     trackedmodel_ptr_id=measure.trackedmodel_ptr_id).excluded_geographical_area
#             except ObjectDoesNotExist:
#                 measure_excluded_geo_area = None
#             try:
#                 order_number_excluded_geo_area = QuotaOrderNumberOriginExclusion.objects.latest_approved().get(
#                     origin_id=quota_number.trackedmodel_ptr_id)
#             except ObjectDoesNotExist:
#                 order_number_excluded_geo_area = None
#             if measure.geographical_area == quota_number.origins and \
#                     measure_excluded_geo_area == order_number_excluded_geo_area:
#                 return True
#
#         return False
