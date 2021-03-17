from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Fixed
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms
from django.core.exceptions import ValidationError

from certificates import models
from common.forms import DateInputFieldFixed
from common.forms import GovukDateRangeField
from common.util import TaricDateRange


class CertificateForm(forms.ModelForm):
    code = forms.CharField(
        label="Certificate ID",
        required=False,
    )
    start_date = DateInputFieldFixed(
        label="Start date",
    )
    end_date = DateInputFieldFixed(
        help_text="Leave empty if a certificate is needed for an unlimited time",
        label="End date",
        required=False,
    )
    sid = forms.CharField(required=False)
    valid_between = GovukDateRangeField(required=False)

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

            if self.instance.valid_between.lower:
                self.fields["start_date"].initial = self.instance.valid_between.lower
            if self.instance.valid_between.upper:
                self.fields["end_date"].initial = self.instance.valid_between.upper

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

        # combine start and end dates into date range
        start_date = cleaned_data.pop("start_date", None)
        end_date = cleaned_data.pop("end_date", None)
        cleaned_data["valid_between"] = TaricDateRange(start_date, end_date)

        return cleaned_data

    class Meta:
        model = models.Certificate
        fields = ("certificate_type", "sid", "valid_between")


class CertificateDescriptionForm(forms.ModelForm):
    valid_between = GovukDateRangeField()

    class Meta:
        model = models.CertificateDescription
        fields = ("description", "valid_between")
