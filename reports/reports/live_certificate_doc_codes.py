import datetime

from django.db.models import Q

from certificates.models import Certificate
from commodities.models import GoodsNomenclatureDescription
from reports.reports.base_table import ReportBaseTable


class Report(ReportBaseTable):
    name = "Live certificate doc codes"

    def headers(self) -> [dict]:
        return [
            {"text": "DOC code"},
            {"text": "description"},
            {"text": "validity start date"},
            {"text": "validity end date"},
        ]

    def row(self, row: GoodsNomenclatureDescription) -> [dict]:

        desc = ""

        if row.descriptions.count() > 0:
            desc = row.descriptions.order_by("-validity_start").first().description

        return [
            {"text": f"{row.certificate_type.sid}{row.sid}"},
            {"text": desc},
            {"text": row.valid_between.lower},
            {"text": row.valid_between.upper},
        ]

    def rows(self) -> [[dict]]:
        table_rows = []
        for row in self.query():
            table_rows.append(self.row(row))

        return table_rows

    def query(self):
        return Certificate.objects.latest_approved().filter(
            Q(
                valid_between__startswith__lte=datetime.date.today(),
                valid_between__endswith__gte=datetime.date.today(),
            )
            | Q(
                valid_between__startswith__lte=datetime.date.today(),
                valid_between__endswith=None,
            ),
        )
        # return Certificate.objects.latest_approved().all()
