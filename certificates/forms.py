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
from common.forms import DescriptionHelpBox
from common.forms import ValidityPeriodForm
from common.forms import delete_form_for
from common.util import get_next_id
from workbaskets.models import WorkBasket


class CertificateCreateForm(ValidityPeriodForm):
    """The form for creating a new certificate."""

    sid = forms.CharField(
        label="Certificate identifer",
        help_text="If another government department has supplied you with a 3 letter identifer, enter it in here.",
        widget=forms.TextInput,
        required=False,
    )

    certificate_type = forms.ModelChoiceField(
        label="Certificate type",
        help_text="Selecting the right certificate type will determine whether it can be associated with measures, commodity codes, or both",
        queryset=models.CertificateType.objects.latest_approved(),
        empty_label="Select a certificate type",
    )

    description = forms.CharField(
        label="Certificate description",
        help_text="You may enter HTML formatting if required. See the guide below for more information.",
        widget=forms.Textarea,
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        self.fields[
            "certificate_type"
        ].label_from_instance = lambda obj: f"{obj.sid} - {obj.description}"

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            "sid",
            "certificate_type",
            "start_date",
            Field.textarea("description", rows=5),
            DescriptionHelpBox(),
            Submit("submit", "Save"),
        )

    def save(self, commit=True):

        instance = super(CertificateCreateForm, self).save(commit=False)

        self.cleaned_data["certificate_description"] = models.CertificateDescription(
            description=self.cleaned_data["description"],
            validity_start=self.cleaned_data["valid_between"].lower,
        )

        current_transaction = WorkBasket.get_current_transaction(self.request)
        if self.cleaned_data["sid"]:
            instance.sid = self.cleaned_data["sid"]
        else:
            instance.sid = get_next_id(
                models.Certificate.objects.filter(
                    sid__regex=r"^[0-9]*$",
                    certificate_type__sid=instance.certificate_type.sid,
                ).approved_up_to_transaction(current_transaction),
                instance._meta.get_field("sid"),
                max_len=3,
            )
        if commit:
            instance.save()
        return instance

    class Meta:
        model = models.Certificate
        fields = ("certificate_type", "valid_between")


class CertificateForm(ValidityPeriodForm):
    """The form for editing a certificate."""

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
