from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Fixed
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms
from django.core.exceptions import ValidationError

from certificates import models
from common.forms import CreateDescriptionForm
from common.forms import DescriptionForm
from common.forms import ValidityPeriodForm
from common.forms import delete_form_for


class CertificateForm(ValidityPeriodForm):
    code = forms.CharField(
        label="Certificate ID",
        required=False,
    )
    sid = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields[
            "certificate_type"
        ].label_from_instance = lambda obj: f"{obj.sid} - {obj.description}"
        self.fields["certificate_type"].required = False

        if self.instance:
            self.fields["code"].disabled = True
            self.fields["code"].help_text = "You can't edit this"
            self.fields["code"].initial = self.instance.code

            self.fields["certificate_type"].disabled = True
            self.fields["certificate_type"].help_text = "You can't edit this"

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL

        self.helper.layout = Layout(
            Field.text(
                "code",
                field_width=Fixed.TEN,
            ),
            "certificate_type",
            "start_date",
            "end_date",
            Submit("submit", "Save"),
        )

    def clean(self):
        cleaned_data = super().clean()

        # extract sid from code
        cleaned_data["sid"] = cleaned_data.pop("code", "")[1:]

        if not cleaned_data["sid"] and self.instance and self.instance.sid:
            cleaned_data["sid"] = self.instance.sid

        if not cleaned_data["sid"]:
            raise ValidationError({"code": "Certificate code is required"})

        # get type from instance if not submitted
        ctype = cleaned_data.get("certificate_type")

        if not ctype and self.instance and self.instance.certificate_type:
            ctype = self.instance.certificate_type

        if not ctype:
            raise ValidationError({"certificate_type": "Certificate type is required"})

        return cleaned_data

    class Meta:
        model = models.Certificate
        fields = ("certificate_type", "sid", "valid_between")


class CertificateDescriptionForm(DescriptionForm):
    class Meta:
        model = models.CertificateDescription
        fields = DescriptionForm.Meta.fields


class CertificateCreateDescriptionForm(CreateDescriptionForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.layout.insert(
            0,
            Field(
                "described_certificate",
                type="hidden",
            ),
        )
        self.fields["description"].label = "Certificate description"

    class Meta:
        model = models.CertificateDescription
        fields = ("described_certificate", "description", "validity_start")


CertificateDeleteForm = delete_form_for(models.Certificate)


CertificateDescriptionDeleteForm = delete_form_for(models.CertificateDescription)
