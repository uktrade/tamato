from datetime import date

from crispy_forms_gds.fields import DateInputField
from django.contrib.postgres.forms.ranges import DateRangeField
from django.core.exceptions import ValidationError


class DateInputFieldFixed(DateInputField):
    def compress(self, data_list):
        day, month, year = data_list or [None, None, None]
        if day and month and year:
            return date(day=int(day), month=int(month), year=int(year))
        else:
            return None


class GovukDateRangeField(DateRangeField):
    base_field = DateInputFieldFixed

    def clean(self, value):
        """Validate the date range input `value` should be a 2-tuple or list or
        datetime objects or None."""
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
