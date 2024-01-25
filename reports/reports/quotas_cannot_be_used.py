import datetime

from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
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
    name = "Quotas Missing Data"
    enabled = True
    description = "Quotas that won't be able to be used by a trader"

    def headers(self) -> [dict]:
        return [
            {"text": "Order number"},
            {"text": "Start date"},
            {"text": "End date"},
            {"text": "Reason"},
        ]

    def row(self, row: QuotaDefinition) -> [dict]:
        return [
            {"text": self.link_renderer_for_quotas(row, row.order_number)},
            {"text": row.valid_between.lower},
            {"text": row.valid_between.upper},
            {"text": row.reason},
        ]

    def rows(self, current_page_data) -> [[dict]]:
        table_rows = []
        for row in current_page_data:
            table_rows.append(self.row(row))

        return table_rows

    def query(self):
        quotas_with_definition_periods = self.get_quotas_with_definition_periods()
        quotas_cannot_be_used = self.find_quotas_that_cannot_be_used(
            quotas_with_definition_periods
        )
        return quotas_cannot_be_used

    def get_quotas_with_definition_periods(self):
        quota_definitions = QuotaDefinition.objects.latest_approved().filter(
            valid_between__isnull=False,
            valid_between__startswith__lte=datetime.datetime.now(),
            valid_between__endswith__gte=datetime.datetime.now(),
        )

        return list(quota_definitions)

    def find_quotas_that_cannot_be_used(self, quotas_with_definition_periods):
        matching_data = set()

        current_time = datetime.datetime.now()

        filter_query = (
            Q(valid_between__endswith__gte=current_time)
            | Q(valid_between__endswith=None)
        ) & Q(valid_between__isnull=False, valid_between__startswith__lte=current_time)

        quota_order_numbers_without_definitions = (
            QuotaOrderNumber.objects.latest_approved()
            .filter(filter_query)
            .exclude(definitions__in=quotas_with_definition_periods)
        )

        matching_data.update(
            quota_order_numbers_without_definitions.exclude(
                order_number__startswith="09"
            )
        )

        for quota in quotas_with_definition_periods:
            if not str(quota.order_number).startswith("09"):
                measures = Measure.objects.latest_approved().filter(
                    order_number=quota.order_number
                )

                if not Exists(measures.filter(order_number=quota.order_number)):
                    matching_data.add(quota.order_number)
                else:
                    quota_order_number = (
                        QuotaOrderNumber.objects.latest_approved()
                        .filter(order_number=quota.order_number)
                        .order_by("-sid")
                        .first()
                    )

                    if quota_order_number:
                        quota_order_number_origin = (
                            QuotaOrderNumberOrigin.objects.latest_approved().filter(
                                order_number_id=quota_order_number.pk
                            )
                        )

                        for origin in quota_order_number_origin:
                            geo_exclusions = QuotaOrderNumberOriginExclusion.objects.latest_approved().filter(
                                origin_id=origin.pk
                            )

                            for geo_exclusion in geo_exclusions:
                                exclusions = MeasureExcludedGeographicalArea.objects.latest_approved().filter(
                                    modified_measure__order_number=quota.order_number,
                                    excluded_geographical_area=geo_exclusion.excluded_geographical_area,
                                )

                                if exclusions.exists():
                                    matching_data.discard(quota)
                                    break
                                else:
                                    matching_data.add(quota.order_number)
        for quota_order_number in matching_data:
            matching_definition = next(
                (
                    quota_definition
                    for quota_definition in quotas_with_definition_periods
                    if quota_definition.order_number == quota_order_number
                ),
                None,
            )

            if matching_definition:
                quota_order_number.reason = "Geographical area/exclusions data does not have any measures with matching data"
            else:
                quota_order_number.reason = "Definition period has not been set"

        return list(matching_data)

    def get_paginated_data(self, page=1, items_per_page=25):
        report_data = self.query()

        paginator = Paginator(report_data, items_per_page)

        try:
            current_page_data = paginator.page(page)
        except PageNotAnInteger:
            current_page_data = paginator.page(1)
        except EmptyPage:
            current_page_data = paginator.page(paginator.num_pages)

        return current_page_data
