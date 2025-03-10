from datetime import date

from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Button
from crispy_forms_gds.layout import Div
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Fieldset
from crispy_forms_gds.layout import Fixed
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms
from django.core.exceptions import ValidationError

from common.forms import DateInputFieldFixed
from common.forms import DateInputFieldTakesParameters
from common.forms import GovukDateRangeField
from common.forms import ValidityPeriodForm
from common.util import TaricDateRange
from reference_documents.models import RefOrderNumber
from reference_documents.models import RefQuotaDefinition
from reference_documents.validators import commodity_code_validator


class RefQuotaDefinitionCreateUpdateForm(
    ValidityPeriodForm,
    forms.ModelForm,
):
    class Meta:
        model = RefQuotaDefinition
        fields = [
            "ref_order_number",
            "commodity_code",
            "duty_rate",
            "volume",
            "measurement",
            "valid_between",
        ]

    def __init__(
        self,
        reference_document_version,
        ref_order_number,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.fields["end_date"].help_text = ""
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
                "volume",
                field_width=Fixed.TWENTY,
            ),
            Field.text(
                "measurement",
                field_width=Fixed.TWENTY,
            ),
            "start_date",
            "end_date",
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    def clean_duty_rate(self):
        error_message = "Duty Rate is not valid - it must have a value"

        if "duty_rate" in self.cleaned_data.keys():
            data = self.cleaned_data["duty_rate"]
            if len(data) < 1:
                raise ValidationError(error_message)
        else:
            raise ValidationError(error_message)

        return data

    def clean_ref_order_number(self):
        error_message = "Quota order number is required"

        if "ref_order_number" in self.cleaned_data.keys():
            data = self.cleaned_data["ref_order_number"]
            if not data:
                raise ValidationError(error_message)
        else:
            raise ValidationError(error_message)

        return data

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
        error_messages={
            "invalid": "Duty rate is invalid",
            "required": "Duty rate is required",
        },
    )

    ref_order_number = forms.ModelChoiceField(
        label="Order number",
        help_text="Select quota order number",
        queryset=RefOrderNumber.objects.all(),
        error_messages={
            "invalid": "Order number is invalid",
        },
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    volume = forms.CharField(
        help_text="Volume",
        widget=forms.TextInput(),
        error_messages={
            "invalid": "Volume invalid",
            "required": "Volume is required",
        },
    )

    measurement = forms.CharField(
        help_text="Measurement",
        error_messages={
            "invalid": "Measurement invalid",
            "required": "Measurement is required",
        },
    )

    end_date = DateInputFieldFixed(
        label="End date",
    )


class RefQuotaDefinitionBulkCreateForm(forms.Form):
    commodity_codes = forms.CharField(
        label="Commodity codes",
        widget=forms.Textarea,
        help_text="Enter one or more commodity codes with each one on a new line.",
        error_messages={
            "invalid": "Commodity code should be 10 digits",
            "required": "Commodity code is required",
        },
    )

    duty_rate = forms.CharField(
        error_messages={
            "invalid": "Duty rate is invalid",
            "required": "Duty rate is required",
        },
    )

    ref_order_number = forms.ModelChoiceField(
        help_text="If the quota order number does not appear, you must first create it for this reference document version.",
        queryset=RefOrderNumber.objects.all(),  # Modified in init
        error_messages={
            "invalid": "Quota order number is invalid",
            "required": "Quota order number is required",
        },
    )

    measurement = forms.CharField(
        error_messages={
            "invalid": "Measurement invalid",
            "required": "Measurement is required",
        },
    )

    def get_variant_index(self, post_data):
        """Looks through post data to see how many validity date / volume
        combinations have been submitted and returns the index value of each
        combination in a list."""
        result = [0]
        if "data" in post_data.keys():
            for key in post_data["data"].keys():
                if key.startswith("start_date_"):
                    variant_index = int(key.replace("start_date_", "").split("_")[0])
                    result.append(variant_index)
            result = list(set(result))
            result.sort()
        return result

    def __init__(
        self,
        reference_document_version,
        ref_order_number=None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.variant_indices = self.get_variant_index(kwargs)
        # Populate order number box if already specified by the URL
        if ref_order_number:
            self.initial["ref_order_number"] = ref_order_number
        # Add fields for the first mandatory date and volume fieldset
        self.fields["start_date_0"] = DateInputFieldFixed(
            label="Start date",
            required=True,
        )
        self.fields["end_date_0"] = DateInputFieldFixed(label="End date", required=True)
        self.fields["volume_0"] = forms.CharField(
            error_messages={
                "invalid": "Volume invalid",
                "required": "Volume is required",
            },
            widget=forms.TextInput(),
            help_text="<br>",
        )
        # Add frontend dynamically added fields to the backend Django form
        for index in self.variant_indices:
            self.fields[f"start_date_{index}_0"] = forms.CharField()
            self.fields[f"start_date_{index}_1"] = forms.CharField()
            self.fields[f"start_date_{index}_2"] = forms.CharField()
            self.fields[f"start_date_{index}"] = DateInputFieldTakesParameters(
                day=self.fields[f"start_date_{index}_0"],
                month=self.fields[f"start_date_{index}_1"],
                year=self.fields[f"start_date_{index}_2"],
                label="Start date",
            )
            self.fields[f"end_date_{index}_0"] = forms.CharField()
            self.fields[f"end_date_{index}_1"] = forms.CharField()
            self.fields[f"end_date_{index}_2"] = forms.CharField()
            self.fields[f"end_date_{index}"] = DateInputFieldTakesParameters(
                day=self.fields[f"end_date_{index}_0"],
                month=self.fields[f"end_date_{index}_1"],
                year=self.fields[f"end_date_{index}_2"],
                label="End date",
            )
            self.fields[f"valid_between_{index}"] = GovukDateRangeField()
            self.fields[f"volume_{index}"] = forms.CharField(
                label="Volume",
                widget=forms.TextInput(),
                help_text="<br>",
            )
        self.fields["ref_order_number"].queryset = (
            RefOrderNumber.objects.all()
            .filter(reference_document_version=reference_document_version)
            .order_by()
        )
        self.fields["ref_order_number"].label_from_instance = (
            lambda obj: f"{obj.order_number}"
        )
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            "ref_order_number",
            Field.text(
                "commodity_codes",
            ),
            Field.text(
                "duty_rate",
                field_width=Fixed.TEN,
            ),
            Field.text(
                "measurement",
                field_width=Fixed.TEN,
            ),
            Fieldset(
                Div(
                    Field(
                        "start_date_0",
                    ),
                ),
                Div(
                    Field(
                        "end_date_0",
                    ),
                ),
                Div(
                    Field(
                        "volume_0",
                        label="Volume",
                        field_width=Fixed.TEN,
                    ),
                ),
                style="display: grid; grid-template-columns: 2fr 2fr 1fr",
                css_class="quota-definition-row",
            ),
            Div(
                Submit(
                    "submit",
                    "Save",
                    data_module="govuk-button",
                    data_prevent_double_click="true",
                ),
                Button.secondary(
                    "",
                    "Add new",
                    css_id="add-new-definition",
                    type="button",
                ),
                css_class="govuk-button-group",
            ),
        )
        # Add dynamically added fields to Django form layout so they do not disappear in the event the form is invalid and reloads
        for index in self.variant_indices[1:]:
            self.helper.layout.insert(
                -1,
                Fieldset(
                    Div(
                        Field(
                            f"start_date_{index}",
                        ),
                    ),
                    Div(
                        Field(
                            f"end_date_{index}",
                        ),
                    ),
                    Div(
                        Field(
                            f"volume_{index}",
                            field_width=Fixed.TEN,
                        ),
                    ),
                    style="display: grid; grid-template-columns: 2fr 2fr 1fr",
                    css_class="quota-definition-row",
                ),
            )

    def clean(self):
        cleaned_data = super().clean()
        # Clean commodity codes
        commodity_codes = cleaned_data.get("commodity_codes")
        if commodity_codes:
            for commodity_code in commodity_codes.splitlines():
                try:
                    commodity_code_validator(commodity_code)
                except ValidationError:
                    self.add_error(
                        "commodity_codes",
                        "Ensure all commodity codes are 10 digits and each on a new line",
                    )
        # Clean validity periods
        for index in self.variant_indices:
            self.custom_clean_validity_period(
                cleaned_data,
                valid_between_field_name=f"valid_between_{index}",
                start_date_field_name=f"start_date_{index}",
                end_date_field_name=f"end_date_{index}",
            )

    def custom_clean_validity_period(
        self,
        cleaned_data,
        valid_between_field_name,
        start_date_field_name,
        end_date_field_name,
    ):
        start_date = cleaned_data.pop(start_date_field_name, None)
        end_date = cleaned_data.pop(end_date_field_name, None)

        # Data may not be present, e.g. if the user skips ahead in the sidebar
        valid_between = self.initial.get(valid_between_field_name)
        if end_date and start_date and end_date < start_date:
            if valid_between:
                if start_date != valid_between.lower:
                    self.add_error(
                        start_date_field_name,
                        "The start date must be the same as or before the end date.",
                    )
                if end_date != self.initial[valid_between_field_name].upper:
                    self.add_error(
                        end_date_field_name,
                        "The end date must be the same as or after the start date.",
                    )
            else:
                self.add_error(
                    end_date_field_name,
                    "The end date must be the same as or after the start date.",
                )
        cleaned_data[valid_between_field_name] = TaricDateRange(start_date, end_date)

        if start_date:
            day, month, year = (start_date.day, start_date.month, start_date.year)
            self.fields[start_date_field_name].initial = date(
                day=int(day),
                month=int(month),
                year=int(year),
            )

        if end_date:
            day, month, year = (end_date.day, end_date.month, end_date.year)
            self.fields[end_date_field_name].initial = date(
                day=int(day),
                month=int(month),
                year=int(year),
            )


class RefQuotaDefinitionDeleteForm(forms.Form):
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
        model = RefQuotaDefinition
        fields = []
