from datetime import date

from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Fixed
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms
from django.core.exceptions import ValidationError

from reference_documents.models import RefOrderNumber
from reference_documents.models import RefQuotaDefinitionRange
from reference_documents.validators import commodity_code_validator


class RefQuotaDefinitionRangeCreateUpdateForm(
    forms.ModelForm,
):
    class Meta:
        model = RefQuotaDefinitionRange
        fields = [
            "ref_order_number",
            "commodity_code",
            "duty_rate",
            "initial_volume",
            "yearly_volume_increment",
            "yearly_volume_increment_text",
            "measurement",
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
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.fields["initial_volume"].help_text = (
            "The initial volume value for the first quota"
        )
        self.fields["yearly_volume_increment"].help_text = (
            "The amount to increase the volume by for subsequent years"
        )
        self.fields["yearly_volume_increment"].help_text = (
            "Text describing the the incrementation if a simple value is not possible"
        )
        self.fields["start_day"].help_text = "The first day of each yearly quota"
        self.fields["start_month"].help_text = "The first month for each yearly quota"
        self.fields["end_day"].help_text = "The last day of each yearly quota"
        self.fields["end_month"].help_text = "The last day of each yearly quota"
        self.fields["start_year"].help_text = "The first year of the quota"
        self.fields["end_year"].help_text = (
            "The last year if the quota, leave blank if there is no end date."
        )
        self.fields["ref_order_number"].help_text = (
            "If the quota order number does not appear, you must first create it for this reference document version."
        )

        if ref_order_number:
            self.initial["ref_order_number"] = ref_order_number

        self.fields["ref_order_number"].queryset = (
            reference_document_version.ref_order_numbers.all()
        )

        self.reference_document_version = reference_document_version
        self.ref_order_number = ref_order_number
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            "ref_order_number",
            Field.text(
                "commodity_code",
                field_width=Fixed.TEN,
            ),
            Field.text(
                "duty_rate",
                field_width=Fixed.THIRTY,
            ),
            Field.text(
                "initial_volume",
                field_width=Fixed.TWENTY,
            ),
            Field.text(
                "yearly_volume_increment",
                field_width=Fixed.TWENTY,
            ),
            Field.text(
                "yearly_volume_increment_text",
                field_width=Fixed.THIRTY,
            ),
            Field.text(
                "measurement",
                field_width=Fixed.TWENTY,
            ),
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
        error_message = f"Start year is not valid, it must be a 4 digit year greater than 2010 and less than {date.today().year + 100}"

        data = self.cleaned_data["start_year"]
        if int(data) < 2010:
            raise ValidationError(error_message)
        elif data > date.today().year + 100:
            raise ValidationError(error_message)

        return data

    def clean_end_year(self):
        error_message = f"End year is not valid, it must be a 4 digit year, greater than 2010, less than {date.today().year + 100} or blank"

        data = None

        if "end_year" in self.cleaned_data.keys():
            data = self.cleaned_data["end_year"]
            if data is not None:
                if data > date.today().year + 100:
                    raise ValidationError(error_message)
                elif data < 2010:
                    raise ValidationError(error_message)
        return data

    def clean_start_day(self):
        error_message = "Start day is not valid, it must be between 1 and 31"

        data = self.cleaned_data["start_day"]
        if not data:
            raise ValidationError(error_message)
        if data < 1 or data > 31:
            raise ValidationError(error_message)

        return data

    def clean_end_day(self):
        error_message = "End day is not valid, it must be between 1 and 31"

        data = self.cleaned_data["end_day"]
        if not data:
            raise ValidationError(error_message)
        if data < 1 or data > 31:
            raise ValidationError(error_message)

        return data

    def clean_end_month(self):
        error_message = "End month is not valid, it must be between 1 and 12"

        data = self.cleaned_data["end_month"]
        if not data:
            raise ValidationError(error_message)
        if data < 1 or data > 12:
            raise ValidationError(error_message)

        return data

    def clean_start_month(self):
        error_message = "Start month is not valid, it must be between 1 and 12"

        data = self.cleaned_data["start_month"]
        if not data:
            raise ValidationError(error_message)
        if data < 1 or data > 12:
            raise ValidationError(error_message)

        return data

    def clean_ref_order_number(self):
        error_message = "Quota order number is required"

        data = self.cleaned_data["ref_order_number"]
        if not data:
            raise ValidationError(error_message)

        return data

    def clean(self):
        error_messages = []

        # check end year >= start year
        if (
            "start_year" in self.cleaned_data.keys()
            and "end_year" in self.cleaned_data.keys()
        ):
            start_year = self.cleaned_data["start_year"]

            end_year = self.cleaned_data["end_year"]

            if end_year is not None:
                if end_year < start_year:
                    error_messages.append(
                        "Invalid year range, start_year is greater than end_year",
                    )
                    self.add_error(
                        "end_year",
                        "Please enter an end year greater than or equal to the start year",
                    )

        if all(
            i in self.cleaned_data.keys()
            for i in ["start_day", "start_month", "end_day", "end_month"]
        ):
            start_month = self.cleaned_data["start_month"]
            start_day = self.cleaned_data["start_day"]
            end_month = self.cleaned_data["end_month"]
            end_day = self.cleaned_data["end_day"]
            start_year = self.cleaned_data["start_year"]
            end_year = self.cleaned_data.get("end_year")

            # validate that the start day and start month are less than the end day and end month
            start_day_month_value = start_day + (100 * start_month)
            end_day_month_value = end_day + (100 * end_month)

            if start_day_month_value > end_day_month_value:
                error_messages.append("Invalid start and end day and month")
                self.add_error(
                    "end_day",
                    "The calculated end date is later than start date in a calendar year",
                )
                self.add_error(
                    "end_month",
                    "The calculated end date is later than start date in a calendar year",
                )
                self.add_error(
                    "start_day",
                    "The calculated end date is later than start date in a calendar year",
                )
                self.add_error(
                    "start_month",
                    "The calculated end date is later than start date in a calendar year",
                )

            # verify that dates work for whole range
            if not end_year:
                end_year = date.today().year + 3

            for index, year in enumerate(range(start_year, end_year)):
                try:
                    date(year, start_month, start_day)
                except ValueError:
                    error_messages.append("Invalid start day and month")
                    self.add_error(
                        "start_day",
                        "The calculated start date is not valid for the year range",
                    )
                    self.add_error(
                        "start_month",
                        "The calculated start date is not valid for the year range",
                    )

                try:
                    date(year, end_month, end_day)
                except ValueError:
                    error_messages.append("Invalid end day and month")
                    self.add_error(
                        "end_day",
                        "The calculated date using the day or month is not valid for the year range",
                    )
                    self.add_error(
                        "end_month",
                        "The calculated date using the day or month is not valid for the year range",
                    )

        if len(error_messages):
            raise forms.ValidationError(" & ".join(error_messages))

    commodity_code = forms.CharField(
        max_length=10,
        help_text="Enter the 10 digit commodity code",
        validators=[commodity_code_validator],
        error_messages={
            "invalid": "Commodity code should be 10 digits",
            "required": "Enter the commodity code",
        },
    )

    duty_rate = forms.CharField(
        help_text="Quota duty rate",
        validators=[],
        error_messages={
            "invalid": "Duty rate is invalid",
            "required": "Duty rate is required",
        },
    )

    ref_order_number = forms.ModelChoiceField(
        label="Order number",
        help_text="Select order number",
        queryset=RefOrderNumber.objects.all(),
        validators=[],
        error_messages={
            "invalid": "Quota order number is invalid",
        },
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    measurement = forms.CharField(
        help_text="Measurement",
        validators=[],
        error_messages={
            "invalid": "Measurement invalid",
            "required": "Measurement is required",
        },
    )

    yearly_volume_increment_text = forms.CharField(
        label="Yearly volume increment text",
        help_text="If the yearly volume increment logic is complex, describe it here",
        validators=[],
        required=False,
    )


class RefQuotaDefinitionRangeDeleteForm(forms.Form):
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
        model = RefQuotaDefinitionRange
        fields = []
