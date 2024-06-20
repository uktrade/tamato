from datetime import date

from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Fixed
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms
from django.core.exceptions import ValidationError

from common.util import TaricDateRange
from reference_documents.models import RefQuotaDefinitionRange, RefQuotaSuspensionRange


class RefQuotaSuspensionRangeCreateUpdateForm(
    forms.ModelForm,
):
    class Meta:
        model = RefQuotaSuspensionRange
        fields = [
            "ref_quota_definition_range",
            "start_day",
            "start_month",
            "end_day",
            "end_month",
            "start_year",
            "end_year",
        ]

    def __init__(
            self,
            reference_document_version,
            ref_order_number,
            ref_quota_definition_range,
            *args,
            **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.fields["start_day"].help_text = "The first day of each yearly suspension"
        self.fields["start_month"].help_text = "The first month for each yearly suspension"
        self.fields["end_day"].help_text = "The last day of each yearly suspension"
        self.fields["end_month"].help_text = "The last day of each yearly suspension"
        self.fields["start_year"].help_text = "The first year of the suspension"
        self.fields["end_year"].help_text = "The last year if the suspension, leave blank if there is no end date."
        self.fields["ref_quota_definition_range"].help_text = (
            "The quota template this suspension relates to"
        )

        self.fields["ref_quota_definition_range"].queryset = (
            RefQuotaDefinitionRange.objects.all().filter(
                ref_order_number__reference_document_version=reference_document_version
            )
        )

        self.reference_document_version = reference_document_version
        self.ref_order_number = ref_order_number
        self.ref_quota_definition_range = ref_quota_definition_range
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            "ref_quota_definition_range",
            Field.text(
                "start_day",
                field_width=Fixed.TWENTY,
            ),
            Field.text(
                "start_month",
                field_width=Fixed.TWENTY,
            ),
            Field.text(
                "end_day",
                field_width=Fixed.TWENTY,
            ),
            Field.text(
                "end_month",
                field_width=Fixed.TWENTY,
            ),
            Field.text(
                "start_year",
                field_width=Fixed.TWENTY,
            ),
            Field.text(
                "end_year",
                field_width=Fixed.TWENTY,
            ),
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    def clean_start_year(self):
        error_message = f"Start year is not valid"

        if "start_year" in self.cleaned_data.keys():
            data = self.cleaned_data["start_year"]
            if int(data) < 2010:
                raise ValidationError(error_message)
            elif data > date.today().year + 100:
                raise ValidationError(error_message)
        else:
            raise ValidationError(error_message)

        return data

    def clean_end_year(self):
        error_message = f"End year is not valid."

        if "end_year" in self.cleaned_data.keys():
            data = self.cleaned_data["end_year"]
            if data is not None:
                if data > date.today().year + 100:
                    raise ValidationError(error_message)
        else:
            raise ValidationError(error_message)

        return data

    def clean_start_day(self):
        error_message = "Start day is not valid, it must be between 1 and 31"

        if "start_day" in self.cleaned_data.keys():
            data = self.cleaned_data["start_day"]
            if not data:
                raise ValidationError(error_message)
            if data < 1 or data > 31:
                raise ValidationError(error_message)
        else:
            raise ValidationError(error_message)

        return data

    def clean_end_day(self):
        error_message = "End day is not valid, it must be between 1 and 31"

        if "end_day" in self.cleaned_data.keys():
            data = self.cleaned_data["end_day"]
            if not data:
                raise ValidationError(error_message)
            if data < 1 or data > 31:
                raise ValidationError(error_message)
        else:
            raise ValidationError(error_message)

        return data

    def clean_end_month(self):
        error_message = "End month is not valid, it must be between 1 and 12"

        if "end_month" in self.cleaned_data.keys():
            data = self.cleaned_data["end_month"]
            if not data:
                raise ValidationError(error_message)
            if data < 1 or data > 12:
                raise ValidationError(error_message)
        else:
            raise ValidationError(error_message)

        return data

    def clean_start_month(self):
        error_message = "Start month is not valid, it must be between 1 and 12"

        if "start_month" in self.cleaned_data.keys():
            data = self.cleaned_data["start_month"]
            if not data:
                raise ValidationError(error_message)
            if data < 1 or data > 12:
                raise ValidationError(error_message)
        else:
            raise ValidationError(error_message)

        return data

    def clean_ref_quota_definition_range(self):
        error_message = "Quota definition range is required"

        if "ref_quota_definition_range" in self.cleaned_data.keys():
            data = self.cleaned_data["ref_quota_definition_range"]
            if not data:
                raise ValidationError(error_message)
        else:
            raise ValidationError(error_message)

        return data

    def clean(self):
        error_messages = []

        # check end year >= start year
        if 'start_year' in self.cleaned_data.keys() and 'end_year' in self.cleaned_data.keys():
            start_year = self.cleaned_data["start_year"]

            end_year = self.cleaned_data["end_year"]

            if end_year is not None:
                if end_year < start_year:
                    error_messages.append('Invalid year range, start_year is greater than end_year')
                    self.add_error("end_year", 'Please enter an end year greater than or equal to the start year')

        if all(i in self.cleaned_data.keys() for i in ['start_day', 'start_month', 'end_day', 'end_month']):
            # validate that the start day and start month are less than the end day and end month
            start_day_month_value = self.cleaned_data["start_day"] + (100 * self.cleaned_data["start_month"])
            end_day_month_value = self.cleaned_data["end_day"] + (100 * self.cleaned_data["end_month"])
            if start_day_month_value > end_day_month_value:
                error_messages.append('Invalid start and end day and month')
                self.add_error("end_day", 'The calculated end date is later than start date in a calendar year')
                self.add_error("end_month", 'The calculated end date is later than start date in a calendar year')
                self.add_error("start_day", 'The calculated end date is later than start date in a calendar year')
                self.add_error("start_month", 'The calculated end date is later than start date in a calendar year')

            # verify that dates work for whole range
            if not self.cleaned_data["end_year"]:
                end_year = date.today().year + 3
            else:
                end_year = self.cleaned_data["end_year"]

            quota_date_ranges = self.cleaned_data["ref_quota_definition_range"].date_ranges()

            for index, year in enumerate(range(self.cleaned_data["start_year"], end_year)):
                try:
                    start_date = date(year, self.cleaned_data["start_month"], self.cleaned_data["start_day"])
                except ValueError:
                    error_messages.append('Invalid start day and month')
                    self.add_error("start_day", 'The calculated start date is not valid for the year range')
                    self.add_error("start_month", 'The calculated start date is not valid for the year range')

                try:
                    if all(i in self.cleaned_data.keys() for i in ['end_day', 'end_month']):
                        end_date = date(year, self.cleaned_data["end_month"], self.cleaned_data["end_day"])
                except ValueError:
                    error_messages.append('Invalid end day and month')
                    self.add_error("end_day", 'The calculated date using the day or month is not valid for the year range')
                    self.add_error("end_month", 'The calculated date using the day or month is not valid for the year range')

                # check that the date exists in a date range from the quota def template
                try:
                    quota_suspension_date_range = TaricDateRange(start_date, end_date)
                    contained = False
                    for quota_date_range in quota_date_ranges:
                        if quota_date_range.contains(quota_suspension_date_range):
                            contained = True
                    if not contained:
                        error_messages.append(f'the suspension date range {quota_suspension_date_range} does not fall within any definition defined by the selected quota definition template')
                except NameError:
                    pass

        if len(error_messages):
            raise forms.ValidationError(' & '.join(error_messages))

    ref_quota_definition_range = forms.ModelChoiceField(
        label="Quota definition range",
        help_text="Select quota definition range",
        queryset=None,
        validators=[],
        error_messages={
            "invalid": "Quota definition range is invalid",
        },
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )


class RefQuotaSuspensionRangeDeleteForm(forms.Form):
    def __init__(self, *args, **kwargs) -> None:
        self.instance = kwargs.pop("instance")
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            Submit(
                "submit",
                "Confirm delete",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    class Meta:
        model = RefQuotaSuspensionRange
        fields = []
