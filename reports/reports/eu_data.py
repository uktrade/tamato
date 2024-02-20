from reports.reports.base_table import ReportBaseTable
from reports.models import EUDataModel

from typing import List, Dict, Union, Optional


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

    def headers(self) -> List[Dict[str, Union[str, str]]]:
        return [
            {
                "field": header.replace("_", " ").capitalize(),
                "filter": "agTextColumnFilter",
            }
            for header in self.headers_list
        ]

    def row(self, row) -> Dict[str, Union[str, Optional[str]]]:
        return {
            field.replace("_", " ").capitalize(): str(getattr(row, field, None))
            for field in self.headers_list
        }

    def rows(self) -> List[Dict[str, Union[str, Optional[str]]]]:
        table_rows = []
        for row in self.query():
            table_rows.append(self.row(row))

        return table_rows

    def query(self):
        try:
            return EUDataModel.objects.all().order_by("goods_code")
        except EUDataModel.DoesNotExist:
            return None
