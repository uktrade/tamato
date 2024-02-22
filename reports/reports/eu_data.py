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

    def headers(self) -> List[Dict[str, Union[str, str]]]:
        return [
            {
                "field": header.replace("_", " ").capitalize(),
                "filter": self.get_filter(header),
            }
            for header in self.headers_list
        ]
    
    def get_filter(self, header):
        if "date" in header:
            return "agDateColumnFilter"
        else:
            return "agTextColumnFilter"

    def row(self, row) -> Dict[str, Union[str, Optional[str]]]:
        updated_row = {}
        for field in self.headers_list:
            value = getattr(row, field, None)
            display_value = self.format_field(field, value)
            updated_row[field.replace("_", " ").capitalize()] = display_value
        return updated_row

    def format_field(self, field: str, value: Optional[str]) -> str:
        if "exists" in field:
            if value == "UNKNOWN":
                return "?"
            elif value == "EXISTS IN TAP":
                return "Y"
            else:
                return "N"
        else:
            return "" if value is None else str(value)

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