from django.db.models import Q

from commodities.models import GoodsNomenclatureDescription
from reports.reports.base_table import ReportBaseTable


class Report(ReportBaseTable):
    name = "Blank Goods Nomenclature descriptions"
    description = (
        "Goods nomenclature objects which have a blank description object attached."
    )

    def headers(self) -> [dict]:
        return [
            {"text": "Commodity code"},
            {"text": "Suffix"},
            {"text": "Start date"},
            {"text": "Description"},
            {"text": "Blank description SID"},
            {"text": "Current description SID"},
            {"text": "Active now"},
            {"text": "Current description"},
        ]

    def row(self, row: GoodsNomenclatureDescription) -> [dict]:
        live_description = (
            row.described_goods_nomenclature.get_description().description
        )
        if row.described_goods_nomenclature.get_description().description:
            live_description = live_description[:50] + "..."
        else:
            live_description = ""

        return [
            {"text": row.described_goods_nomenclature.item_id},
            {"text": row.described_goods_nomenclature.suffix},
            {"text": f"{row.validity_start:%d %b %Y}"},
            {"text": row.description},
            {"text": row.sid},
            {"text": row.described_goods_nomenclature.get_description().sid},
            {"text": row.sid == row.described_goods_nomenclature.get_description().sid},
            {"text": live_description},
        ]

    def rows(self) -> [[dict]]:
        table_rows = []
        for row in self.query():
            table_rows.append(self.row(row))

        return table_rows

    def query(self):
        return GoodsNomenclatureDescription.objects.latest_approved().filter(
            Q(description="") | Q(description=None),
        )
