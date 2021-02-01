import logging
from datetime import date

from django import forms
from django.contrib.postgres.forms.ranges import DateRangeField
from django.core.exceptions import ValidationError
from django.forms.utils import from_current_timezone

from common import validators


log = logging.getLogger(__name__)


class GovukDateWidget(forms.MultiWidget):
    def __init__(self, attrs=None):
        widgets = (
            forms.NumberInput(attrs=attrs),
            forms.NumberInput(attrs=attrs),
            forms.NumberInput(attrs=attrs),
        )
        super().__init__(widgets=widgets, attrs=attrs)

    def decompress(self, value):
        if value:
            return [value.day, value.month, value.year]
        return ["", "", ""]


class GovukDateField(forms.MultiValueField):
    widget = GovukDateWidget

    def __init__(self, **kwargs):
        fields = (
            forms.CharField(),
            forms.CharField(),
            forms.CharField(),
        )
        super().__init__(fields=fields, require_all_fields=True, **kwargs)

    def compress(self, data_list):
        if data_list:
            if not all(data_list):
                raise ValidationError("Enter a valid date.", code="invalid_date")

            try:
                day, month, year = data_list
                result = date(int(year), int(month), int(day))
            except ValueError as e:
                raise ValidationError("Enter a valid date.", code="invalid_date") from e

            return result


class GovukDateRangeField(DateRangeField):
    base_field = GovukDateField

    def clean(self, value):
        """
        Validate the date range input
        `value` should be a 2-tuple or list or datetime objects or None
        """
        clean_data = []
        errors = []
        if self.disabled and not isinstance(value, list):
            value = self.widget.decompress(value)

        # start date is always required
        if not value:
            raise ValidationError(self.error_messages["required"], code="required")

        # somehow we didn't get a list or tuple of datetimes
        if not isinstance(value, (list, tuple)):
            raise ValidationError(self.error_messages["invalid"], code="invalid")

        for i, (field, value) in enumerate(zip(self.fields, value)):
            limit = ("start", "end")[i]

            if value in self.empty_values and (
                limit == "lower" or self.require_all_fields
            ):
                error = ValidationError(
                    self.error_messages[f"{limit}_required"],
                    code=f"{limit}_required",
                )
                error.subfield = i
                raise error

            try:
                clean_data.append(field.clean(value))
            except ValidationError as e:
                for error in e.error_list:
                    if "Enter a valid date" in str(error):
                        error.message = f"Enter a valid {limit} date."
                    error.subfield = i
                    errors.append(error)

        if errors:
            raise ValidationError(errors)

        out = self.compress(clean_data)
        self.validate(out)
        self.run_validators(out)
        return out
