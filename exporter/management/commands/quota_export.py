from collections import defaultdict
from datetime import date
from typing import Any
from typing import Optional

import xlsxwriter
from django.contrib.postgres.aggregates import StringAgg
from django.core.management import BaseCommand
from django.core.management.base import CommandParser
from django.db.models.expressions import Value
from django.db.models.fields import DateField
from django.db.models.fields import Field
from django.db.models.functions import Concat
from django.db.models.functions import NullIf
from django.db.models.functions.text import Lower
from django.db.models.functions.text import Upper
from django.db.models.query import QuerySet

from importer.models import ImportBatch
from quotas.models import QuotaDefinition
from quotas.models import QuotaOrderNumber

FORMATS = defaultdict(
    dict,
    {
        "DecimalField": {"num_format": "#,##0.00"},
        "IntegerField": {"num_format": "0"},
        "CharField": {"num_format": 49},
        "TextField": {"num_format": 49, "text_wrap": True},
        "DateField": {"num_format": "yyyy-mm-dd"},
    },
)


def get_queryset_field(qs: QuerySet, name: str) -> Field:
    if name in qs.query.annotations:
        col = qs.query.annotations[name]
        return col.output_field

    if "__" in name:
        contained_model = qs.model
        for step in name.split("__"):
            relation = {
                **contained_model._meta.fields_map,
                **contained_model._meta._forward_fields_map,
            }[step]
            contained_model = relation.related_model or relation
        return contained_model

    return qs.model._meta.get_field(name)


class Command(BaseCommand):
    def add_arguments(self, parser: CommandParser) -> None:
        command_name = self.__class__.__module__.split(".")[-1]
        last_batch = ImportBatch.objects.order_by("-created_at").first().name
        parser.add_argument(
            "output",
            type=str,
            nargs="?",
            default=f"{command_name}_{date.today().isoformat()}-DIT{last_batch}.xlsx",
        )
        super().add_arguments(parser)

    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        wb = options["workbasket"]
        querysets = (
            QuotaOrderNumber.objects.approved_up_to_transaction(wb.current_transaction)
            .filter(order_number__startswith="05")
            .annotate(
                geo_origins=StringAgg("origins__area_id", ", ", distinct=True),
                geo_exclusions=StringAgg(
                    "quotaordernumberorigin__excluded_areas__area_id",
                    ", ",
                    distinct=True,
                ),
                commodities=StringAgg(
                    "measure__goods_nomenclature__item_id",
                    ", ",
                    distinct=True,
                ),
                measure_types=StringAgg(
                    "measure__measure_type__description",
                    ", ",
                    distinct=True,
                ),
            )
            .values(
                "sid",
                "order_number",
                "geo_origins",
                "geo_exclusions",
                "commodities",
                "measure_types",
            ),
            QuotaDefinition.objects.approved_up_to_transaction(wb.current_transaction)
            .filter(order_number__order_number__startswith="05")
            .annotate(
                validity_start=Lower("valid_between", output_field=DateField()),
                validity_end=Upper("valid_between", output_field=DateField()),
                sub_quotas_str=StringAgg(
                    "sub_quotas__order_number__order_number",
                    ", ",
                    distinct=True,
                ),
                suspensions=StringAgg(
                    NullIf(
                        Concat(
                            Lower("quotasuspension__valid_between"),
                            Value(" – "),
                            Upper("quotasuspension__valid_between"),
                        ),
                        Value(" – "),
                    ),
                    ", ",
                    distinct=True,
                ),
            )
            .values(
                "sid",
                "order_number__order_number",
                "validity_start",
                "validity_end",
                "initial_volume",
                "measurement_unit__code",
                "measurement_unit_qualifier__code",
                "sub_quotas_str",
                "suspensions",
            ),
        )

        with xlsxwriter.Workbook(options["output"]) as workbook:
            for qs in querysets:
                print(str(qs.query))
                name = str(qs.model._meta.verbose_name_plural).capitalize()
                sheet = workbook.add_worksheet(name=name)
                sheet.write_row(0, 0, qs._fields)
                for col, field_name in enumerate(qs._fields):
                    field = get_queryset_field(qs, field_name)
                    format = workbook.add_format(FORMATS[field.get_internal_type()])
                    sheet.set_column(col, col, None, format)
                for row, object in enumerate(qs.iterator(), start=1):
                    sheet.write_row(row, 0, [object[k] for k in qs._fields])
