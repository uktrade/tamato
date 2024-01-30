from reports.reports.base_table import ReportBaseTable
from reports.models import EUDataModel

from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage


class Report(ReportBaseTable):
    name = "Table report of EU data"
    description = "Imported data from the EU tariff using the upload CSV feature"
    enabled = True

    headers_list = [
        "goods_code",
        "add_code",
        "order_no",
        "start_date",
        "end_date",
        "red_ind",
        "origin",
        "measure_type",
        "legal_base",
        "duty",
        "origin_code",
        "meas_type_code",
        "goods_nomenclature_exists",
        "geographical_area_exists",
        "measure_type_exists",
        "measure_exists",
    ]

    headers_list = sorted(headers_list)

    def headers(self) -> [dict]:
        return [
            {"field": header.replace("_", " ").capitalize(), "filter": 'agTextColumnFilter'}
            for header in self.headers_list
        ]

    def row(self, row) -> [dict]:
        return {field.replace("_", " ").capitalize(): str(getattr(row, field, None)) for field in self.headers_list}

    def rows(self, current_page_data) -> [dict]:
        table_rows = []
        for row in current_page_data:
            table_rows.append(self.row(row))

        return table_rows

    def query(self):
        return EUDataModel.objects.all().order_by("goods_code")

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
