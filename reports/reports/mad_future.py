from open_data.models.report_models import ReportMeasureAsDefinedReport
from open_data.utils import get_report_timestamp_str
from reports.reports.base_text import ReportBaseText


class Report(ReportBaseText):
    name = "Measures as defined"
    description = (
        "Measures as defined, including future measures. "
        "<br>The report is too large to display: use 'Export to csv' to download it."
    )
    download_csv = True

    def text(self):
        return get_report_timestamp_str()

    def headers(self) -> [dict]:
        return [
            {"text": "id"},
            {"text": "trackedmodel_ptr_id"},
            {"text": "commodity__sid"},
            {"text": "commodity__code"},
            {"text": "commodity__indent"},
            {"text": "commodity__description"},
            {"text": "measure__sid"},
            {"text": "measure__type__id"},
            {"text": "measure__type__description"},
            {"text": "measure__additional_code__code"},
            {"text": "measure__additional_code__description"},
            {"text": "measure__duty_expression"},
            {"text": "measure__effective_start_date"},
            {"text": "measure__effective_end_date"},
            {"text": "measure__reduction_indicator"},
            {"text": "measure__footnotes"},
            {"text": "measure__conditions"},
            {"text": "measure__geographical_area__sid"},
            {"text": "measure__geographical_area__id"},
            {"text": "measure__geographical_area__description"},
            {"text": "measure__excluded_geographical_areas__ids"},
            {"text": "measure__excluded_geographical_areas__descriptions"},
            {"text": "measure__quota__order_number"},
            {"text": "measure__regulation__id"},
            {"text": "measure__regulation__url"},
        ]

    def row(self, row: ReportMeasureAsDefinedReport) -> [dict]:
        return [
            {"text": row.id},
            {"text": row.commodity_sid},
            {"text": row.commodity_code},
            {"text": row.commodity_indent},
            {"text": row.commodity_description},
            {"text": row.measure_sid},
            {"text": row.measure_type_id},
            {"text": row.measure_type_description},
            {"text": row.measure_additional_code_code},
            {"text": row.measure_additional_code_description},
            {"text": row.measure_duty_expression},
            {"text": row.measure_effective_start_date},
            {"text": row.measure_effective_end_date},
            {"text": row.measure_reduction_indicator},
            {"text": row.measure_footnotes},
            {"text": row.measure_conditions},
            {"text": row.measure_geographical_area_sid},
            {"text": row.measure_geographical_area_id},
            {"text": row.measure_geographical_area_description},
            {"text": row.measure_excluded_geographical_areas_ids},
            {"text": row.measure_excluded_geographical_areas_descriptions},
            {"text": row.measure_quota_order_number},
            {"text": row.measure_regulation_id},
            {"text": row.measure_regulation_url},
        ]

    def rows(self) -> [[dict]]:
        table_rows = []
        for row in self.query():
            table_rows.append(self.row(row))

        return table_rows

    def query(self):
        return ReportMeasureAsDefinedReport.objects.all()
