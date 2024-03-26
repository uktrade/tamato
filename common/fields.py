"""Common field types."""

from typing import Union

from dateutil.relativedelta import relativedelta
from django.contrib.postgres.fields import DateRangeField
from django.contrib.postgres.fields import DateTimeRangeField
from django.db import models
from django.db.models.expressions import RawSQL
from django.forms import ModelChoiceField
from django.urls import reverse_lazy
from psycopg2.extras import DateRange

from common import validators
from common.util import TaricDateRange
from common.util import TaricDateTimeRange
from common.widgets import AutocompleteWidget


def get_next_by_max(field):
    return lambda: RawSQL(
        sql=f'SELECT COALESCE(MAX("{field.column}"), 0) + 1 FROM "{field.model._meta.db_table}"',
        params=[],
    )


class NumericSID(models.PositiveIntegerField):
    def __init__(self, *args, **kwargs):
        kwargs["editable"] = False
        kwargs["validators"] = [validators.NumericSIDValidator()]
        kwargs["db_index"] = True
        kwargs.setdefault("default", get_next_by_max(self))
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs["editable"]
        del kwargs["validators"]
        del kwargs["db_index"]
        del kwargs["default"]
        return name, path, args, kwargs


class SignedIntSID(models.IntegerField):
    def __init__(self, *args, **kwargs):
        kwargs["editable"] = False
        kwargs["db_index"] = True
        kwargs.setdefault("default", get_next_by_max(self))
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs["editable"]
        del kwargs["db_index"]
        del kwargs["default"]
        return name, path, args, kwargs


class ShortDescription(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 500
        kwargs["blank"] = True
        kwargs["null"] = True
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs["max_length"]
        del kwargs["blank"]
        del kwargs["null"]
        return name, path, args, kwargs


class LongDescription(models.TextField):
    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 20000
        kwargs["blank"] = True
        kwargs["null"] = True
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs["max_length"]
        del kwargs["blank"]
        del kwargs["null"]
        return name, path, args, kwargs


class ApplicabilityCode(models.PositiveSmallIntegerField):
    def __init__(self, *args, **kwargs):
        kwargs["choices"] = validators.ApplicabilityCode.choices
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs["choices"]
        return name, path, args, kwargs


class TaricDateRangeField(DateRangeField):
    range_type = TaricDateRange

    def from_db_value(
        self,
        value: Union[DateRange, TaricDateRange],
        *_args,
        **_kwargs,
    ) -> TaricDateRange:
        """
        By default Django ignores the range_type and just returns a Psycopg2
        DateRange.

        This method forces the conversion to a TaricDateRange and shifts the
        upper date to be inclusive (it is exclusive by default).
        """
        if not isinstance(value, DateRange):
            return value
        lower = value.lower
        upper = value.upper
        if not value.upper_inc and not value.upper_inf:
            upper = upper - relativedelta(days=1)
        return TaricDateRange(lower=lower, upper=upper)


class TaricDateTimeRangeField(DateTimeRangeField):
    range_type = TaricDateTimeRange


class AutoCompleteField(ModelChoiceField):
    def __init__(self, *args, **kwargs):
        qs = kwargs["queryset"]
        prefix = getattr(qs.model, "url_pattern_name_prefix", None)
        if not prefix:
            prefix = qs.model._meta.model_name
        self.widget = AutocompleteWidget(
            attrs={
                "label": kwargs.get("label", ""),
                "help_text": kwargs.get("help_text", ""),
                "source_url": reverse_lazy(f"{prefix}-list"),
                **kwargs.pop("attrs", {}),
            },
        )
        super().__init__(*args, **kwargs)

    def prepare_value(self, value):
        return self.to_python(value)
