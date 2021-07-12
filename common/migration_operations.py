from django.db.migrations.operations.base import Operation
from django.db.models import F
from django.db.models import Func
from django.db.models.expressions import Value
from django.db.models.functions import Lower

from common.fields import TaricDateRangeField


def keep_bounds(field_name):
    return (
        f"IF lower_inf({field_name}) THEN '(' ELSE '[' END IF"
        f"||IF upper_inf({field_name}) THEN ')' ELSE ']' END IF"
    )


def daterange_from_tstzrange(field_name):
    return "daterange(" f"lower({field_name})::date," f"upper({field_name})::date" f")"


def tstzrange_from_daterange(field_name):
    return (
        "tstzrange("
        f"lower({field_name}) + time with time zone '00:00:00 UTC',"
        f"upper({field_name}) + time with time zone '23:59:59 UTC'"
        f")"
    )


def change_range_type(table_name, field_name, to_type, conversion):
    from django.conf import settings

    if settings.SQLITE:
        return ""
    return (
        f"ALTER TABLE {table_name} "
        f"ALTER COLUMN {field_name} "
        f"SET DATA TYPE {to_type} USING {conversion(field_name)}"
    )


class ConvertTaricDateRange(Operation):
    """
    Migration operation which converts TaricDateTimeRangeFields to
    TaricDateRangeField.

    This is required because Postgres does not automatically cast tstzranges to
    dateranges and vice versa. Neither does it cast from timestamp with time zone values
    to date values.

    This class is a reversible migration operation which converts the column type with
    ALTER COLUMN TYPE USING to preserve the data. There is some loss in the conversion -
    times and timezones are truncated when converting to dates. When converting back to
    tstzrange, start times are set to 00:00:00, end times are set to 23:59:59 and
    timezones are set to UTC. Range bounds (inclusive/exclusive) are preserved.

    XXX: This operation does not currently handle empty ranges
    """

    reversible = True

    def __init__(self, model_name, name, **kwargs):
        self.name = name
        self.model_name = model_name.lower()
        self.kwargs = kwargs

    def state_forwards(self, app_label, state):
        state.models[app_label, self.model_name].fields[
            self.name
        ] = TaricDateRangeField(
            db_index=True,
            blank=self.kwargs.get("blank", False),
            null=self.kwargs.get("null", False),
        )
        state.reload_model(app_label, self.model_name, delay=True)

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        schema_editor.execute(
            change_range_type(
                f"{app_label}_{self.model_name}",
                self.name,
                to_type="daterange",
                conversion=daterange_from_tstzrange,
            ),
        )

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        schema_editor.execute(
            change_range_type(
                f"{app_label}_{self.model_name}",
                self.name,
                to_type="tstzrange",
                conversion=tstzrange_from_daterange,
            ),
        )

    def describe(self):
        return "Converts a tstzrange column to a daterange column"

    @property
    def migration_name_fragment(self):
        return f"convert_taric_date_range_{self.name}"


def copy_start_date_to_validity_start(app_name, model_name):
    def copy(apps, schema_editor):
        Model = apps.get_model(app_name, model_name)
        Model.objects.update(validity_start=Lower("valid_between"))

    return copy


def copy_start_date_to_valid_between(app_name, model_name):
    def copy(apps, schema_editor):
        Model = apps.get_model(app_name, model_name)
        Model.objects.update(
            valid_between=Func(
                F("validity_start"),
                None,
                Value("[]"),
                function="DATERANGE",
            ),
        )

    return copy
