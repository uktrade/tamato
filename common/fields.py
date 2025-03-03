"""Common field types."""

from typing import Union

from dateutil.relativedelta import relativedelta
from django.contrib.postgres.fields import DateRangeField
from django.contrib.postgres.fields import DateTimeRangeField
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.expressions import RawSQL
from django.forms import ModelChoiceField
from django.urls import reverse_lazy
from psycopg.types.range import DateRange
from psycopg.types.range import Range

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
    """Model field that converts between `common.util.TaricDateRange` and its
    database representation."""

    range_type = TaricDateRange

    def from_db_value(
        self,
        value: Union[Range, DateRange, TaricDateRange],
        *_args,
        **_kwargs,
    ) -> TaricDateRange:
        """
        By default Django ignores the range_type and just returns a Psycopg
        DateRange.

        Additionally, from the Psycopg docs
        (https://www.psycopg.org/psycopg3/docs/basic/pgtypes.html#range-adaptation):

            All the PostgreSQL range types are loaded as the Range Python type,
            which is a Generic type and can hold bounds of different types.

        This method forces the conversion to a TaricDateRange and shifts the
        upper date to be inclusive (it is exclusive by default).
        """

        if not value:
            return value

        if isinstance(value, TaricDateRange):
            # Avoid re-applying the date shift / inclusive bound change to
            # `upper` (i.e. a TaricDateRange instance implies a shift has
            # already been applied).
            return value

        lower = value.lower
        upper = value.upper
        if not value.upper_inc and not value.upper_inf:
            upper = upper - relativedelta(days=1)

        return TaricDateRange(lower=lower, upper=upper)


class TaricDateTimeRangeField(DateTimeRangeField):
    range_type = TaricDateTimeRange


class AutoCompleteField(ModelChoiceField):
    """
    A form field that provides an AutoComplete widget for selecting a model
    instance.

    Args:
    - queryset (QuerySet): A queryset of model instances that will populate the valid choices for the field.
    - label (str): (Optional) A label for the field.
    - help_text (str): (Optional) Help text for the field.
    - url_pattern_name (str): (Optional) A custom pattern name to use for resolving the API source URL of AutoCompleteWidget.
    - attrs (dict): (Optional) Additional attributes to pass to AutoCompleteWidget, e.g  {"min-length": 2}.
    """

    def __init__(self, queryset, url_pattern_name=None, *args, **kwargs):
        self.widget = AutocompleteWidget(
            attrs={
                "label": kwargs.get("label", ""),
                "help_text": kwargs.get("help_text", ""),
                "source_url": reverse_lazy(
                    self.get_url_pattern_name(queryset, url_pattern_name),
                ),
                **kwargs.pop("attrs", {}),
            },
        )
        super().__init__(queryset=queryset, *args, **kwargs)

    def get_url_pattern_name(self, queryset, url_pattern_name: str | None) -> str:
        """
        Determines the URL pattern name to use for resolving the API source URL
        of AutocompleteWidget.

        If a custom name isn't provided, the name will be based on the
        attributes of the model derived from the queryset.
        """

        if url_pattern_name is not None:
            return url_pattern_name

        prefix = getattr(queryset.model, "url_pattern_name_prefix", None)
        if not prefix:
            prefix = queryset.model._meta.model_name

        return f"{prefix}-list"

    def prepare_value(self, value):
        try:
            return self.to_python(value)
        except ValidationError:
            return None
