from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Fixed
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms

from common.forms import DateInputFieldFixed
from common.forms import ValidityPeriodForm
from reference_documents import models
from reference_documents.models import PreferentialRate
from reference_documents.validators import commodity_code_validator


class PreferentialRateEditForm(
    ValidityPeriodForm,
    forms.ModelForm,
):
    class Meta:
        model = PreferentialRate
        fields = [
            "commodity_code",
            "duty_rate",
            "valid_between",
        ]

    commodity_code = forms.CharField(
        help_text="Commodity Code",
        validators=[commodity_code_validator],
        error_messages={
            "invalid": "Commodity code should be 10 digits",
            "required": "Enter the commodity code",
        },
    )

    duty_rate = forms.CharField(
        help_text="Duty Rate",
        validators=[],
        error_messages={
            "invalid": "Duty rate is invalid",
            "required": "This is required",
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.init_layout()
        self.init_fields()

    def init_layout(self):
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            "commodity_code",
            "duty_rate",
            "start_date",
            "end_date",
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    def init_fields(self):
        pass

    def clean(self):
        return super().clean()


class ReferenceDocumentCreateUpdateForm(forms.ModelForm):
    title = forms.CharField(
        label="Reference Document title",
        error_messages={
            "required": "A Reference Document title is required",
            "unique": "A Reference Document with this title already exists",
        },
    )
    area_id = forms.CharField(
        label="Area ID",
        error_messages={
            "required": "An area ID is required",
            "unique": "A Reference Document with this area ID already exists",
            "max_length": "The area ID can be at most 4 characters long",
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields[
            "title"
        ].help_text = "For example, 'Reference document for XX' where XX is the Area ID"
        self.fields["area_id"].help_text = "Two character ID for the area referenced"

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL

        self.helper.layout = Layout(
            Field.text(
                "title",
                field_width=Fixed.TWENTY,
            ),
            Field.text(
                "area_id",
                field_width=Fixed.TEN,
            ),
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    class Meta:
        model = models.ReferenceDocument
        fields = ["title", "area_id"]


class ReferenceDocumentDeleteForm(forms.Form):
    def __init__(self, *args, **kwargs) -> None:
        self.instance = kwargs.pop("instance")
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        reference_document = self.instance
        versions = models.ReferenceDocumentVersion.objects.all().filter(
            reference_document=reference_document,
        )
        if versions:
            raise forms.ValidationError(
                f"Reference Document {reference_document.area_id} cannot be deleted as it has"
                f" active versions.",
            )

        return cleaned_data


class PreferentialRateCreateForm(
    ValidityPeriodForm,
    forms.ModelForm,
):
    class Meta:
        model = PreferentialRate
        fields = [
            "commodity_code",
            "duty_rate",
            "valid_between",
            "reference_document_version",
        ]

    commodity_code = forms.CharField(
        help_text="Commodity Code",
        validators=[commodity_code_validator],
        error_messages={
            "invalid": "Commodity code should be 10 digits",
            "required": "Enter the commodity code",
        },
    )

    duty_rate = forms.CharField(
        help_text="Duty Rate",
        validators=[],
        error_messages={
            "invalid": "Duty rate is invalid",
            "required": "This is required",
        },
    )

    reference_document_version = forms.CharField(widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.init_layout()
        self.init_fields()

    def init_layout(self):
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            "commodity_code",
            "duty_rate",
            "start_date",
            "end_date",
            Submit(
                "submit",
                "Create",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    def init_fields(self):
        pass

    def clean(self):
        return super().clean()


class PreferentialRateDeleteForm(forms.ModelForm):
    class Meta:
        model = PreferentialRate
        fields = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.init_layout()
        self.init_fields()

    def init_layout(self):
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            Submit(
                "submit",
                "Confirm Delete",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    def init_fields(self):
        pass

    def clean(self):
        return super().clean()


class ReferenceDocumentVersionsEditCreateForm(forms.ModelForm):
    version = forms.CharField(
        label="Version number",
        error_messages={
            "required": "A version number is required",
            "invalid": "Version must be a number",
        },
    )
    published_date = DateInputFieldFixed(
        label="Published date",
    )
    entry_into_force_date = DateInputFieldFixed(
        label="Entry into force date",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL

        self.helper.layout = Layout(
            Field(
                "reference_document",
                type="hidden",
            ),
            Field.text(
                "version",
                field_width=Fixed.TEN,
            ),
            "published_date",
            "entry_into_force_date",
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    class Meta:
        model = models.ReferenceDocumentVersion
        fields = [
            "reference_document",
            "version",
            "published_date",
            "entry_into_force_date",
        ]
