from datetime import date
from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.core.exceptions import ObjectDoesNotExist

from reports.reports.base_chart import ReportBaseChart

from quotas.models import QuotaOrderNumber, QuotaDefinition, QuotaOrderNumberOriginExclusion
from measures.models import Measure, MeasureExcludedGeographicalArea

from collections import defaultdict


# Third attempt - Ensure everything is cached.. hopefully speeds it up!
class Report(ReportBaseChart):
    name = "Quotas Missing Data"
    description = "This report shows the quotas that cannot be used by traders due to missing data"
    report_template = "text"
    hover_text = "approved"
    chart_type = "line"
    days_in_past = 365

    def data(self):
        result = []

        for row in self.query():
            result.append({"y": row["count"], "x": str(row["date"])})

        return result

    def labels(self):
        return []

    def query(self):
        approved_quota_sids = self.get_approved_quota_sids()

        quotas_with_definition_periods = self.get_quotas_with_definition_periods(approved_quota_sids)

        quotas_can_be_used = self.find_quotas_that_can_be_used(quotas_with_definition_periods)

        return quotas_can_be_used

    def get_approved_quota_sids(self):
        return QuotaOrderNumber.objects.latest_approved().all()

    def get_quotas_with_definition_periods(self, approved_quota_sids):
        quotas_with_periods = []
        quota_definitions_cache = defaultdict(list)

        for quota_number in approved_quota_sids:
            quota_definitions = QuotaDefinition.objects.latest_approved().filter(order_number=quota_number)
            quota_definitions_cache[quota_number].extend(quota_definitions)

        for quota_number, quota_definitions in quota_definitions_cache.items():
            for quota in quota_definitions:
                if quota.valid_between:
                    quotas_with_periods.append(quota)

        return quotas_with_periods

    def find_quotas_that_can_be_used(self, quotas_with_definition_periods):
        quotas_can_be_used = []

        measure_cache = defaultdict(list)
        excluded_geo_area_cache = defaultdict(dict)

        for quota in quotas_with_definition_periods:
            quotas = QuotaOrderNumber.objects.latest_approved().filter(sid=quota.sid)

            for quota_number in quotas:
                if quota_number in measure_cache:
                    measures = measure_cache[quota_number]
                else:
                    measures = Measure.objects.latest_approved().filter(order_number=quota_number)
                    measure_cache[quota_number] = measures

                for measure in measures:
                    if measure.trackedmodel_ptr_id in excluded_geo_area_cache:
                        measure_excluded_geo_area = excluded_geo_area_cache[measure.trackedmodel_ptr_id]
                    else:
                        try:
                            measure_excluded_geo_area = MeasureExcludedGeographicalArea.current_objects.get(
                                trackedmodel_ptr_id=measure.trackedmodel_ptr_id).excluded_geographical_area
                        except ObjectDoesNotExist:
                            measure_excluded_geo_area = None
                        excluded_geo_area_cache[measure.trackedmodel_ptr_id] = measure_excluded_geo_area

                    if quota_number.trackedmodel_ptr_id in excluded_geo_area_cache:
                        order_number_excluded_geo_area = excluded_geo_area_cache[quota_number.trackedmodel_ptr_id]
                    else:
                        try:
                            order_number_excluded_geo_area = QuotaOrderNumberOriginExclusion.objects.latest_approved().get(
                                origin_id=quota_number.trackedmodel_ptr_id)
                        except ObjectDoesNotExist:
                            order_number_excluded_geo_area = None
                        excluded_geo_area_cache[quota_number.trackedmodel_ptr_id] = order_number_excluded_geo_area

                    if measure.geographical_area == quota_number.origins and \
                            measure_excluded_geo_area == order_number_excluded_geo_area:
                        quotas_can_be_used.append(quota_number.sid)

        return quotas_can_be_used

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
