from itertools import chain
from typing import Any
from typing import Iterable
from typing import Optional

from django.apps import apps
from django.conf import settings
from django.core.management import BaseCommand
from django.db.models.fields import BooleanField
from django.db.models.fields import Field

from common.fields import TaricDateRangeField
from common.models.mixins.validity import ValidityMixin


def field_to_expr(field: Field) -> Iterable[str]:
    column = f'\\"{field.column}\\"'
    if isinstance(field, TaricDateRangeField):
        return [f"UPPER({column})", f"LOWER({column})"]
    elif isinstance(field, BooleanField):
        return [f"CASE WHEN {column} IS TRUE THEN 1 ELSE 0 END"]
    else:
        return [column]


class Command(BaseCommand):
    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        names = (name.split(".")[0] for name in settings.DOMAIN_APPS)
        models = chain(*[apps.get_app_config(name).get_models() for name in names])
        database = settings.DATABASES["default"]

        print(".echo on")
        print(".mode csv")
        for model in models:
            fields = model._meta.local_fields

            # Take out the validity field and put it at the end
            if issubclass(model, ValidityMixin):
                validity_field = model._meta.get_field(
                    ValidityMixin.valid_between.field.name,
                )
                fields.remove(validity_field)
                fields.append(validity_field)

            field_names = ", ".join(chain(*[field_to_expr(f) for f in fields]))

            print(
                ".import '|psql -c \"COPY (SELECT {1} FROM {2}) TO STDOUT (FORMAT csv);\" {0[NAME]}' {2}".format(
                    database,
                    field_names,
                    model._meta.db_table,
                ),
            )

        print("VACUUM;")
