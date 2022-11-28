from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Fixed
from crispy_forms_gds.layout import Fluid
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms
from django.db.models import Max

from additional_codes import models
from common.forms import CreateDescriptionForm
from common.forms import DescriptionForm
from common.forms import DescriptionHelpBox
from common.forms import ValidityPeriodForm
from common.forms import delete_form_for
from workbaskets.models import WorkBasket


class AdditionalCodeForm(ValidityPeriodForm):
    code = forms.CharField(
        label="Additional code ID",
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields[
            "type"
        ].label_from_instance = lambda obj: f"{obj.sid} - {obj.description}"
        self.fields["type"].label = "Additional code type"
        self.fields["type"].required = False

        if self.instance.pk is not None:
            self.fields["code"].disabled = True
            self.fields["code"].help_text = "You can't edit this"
            self.fields[
                "code"
            ].initial = f"{self.instance.type.sid}{self.instance.code}"

            self.fields["type"].disabled = True
            self.fields["type"].help_text = "You can't edit this"

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL

        self.helper.layout = Layout(
            Field.text(
                "code",
                field_width=Fixed.TEN,
            ),
            Field("type"),
            Field("start_date"),
            Field("end_date"),
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    def clean(self):
        cleaned_data = super().clean()

        if self.instance and self.instance.sid:
            cleaned_data["sid"] = self.instance.sid

        # get type from instance if not submitted
        ctype = cleaned_data.get("type")
        if not ctype and self.instance.pk and self.instance.type:
            ctype = self.instance.type

        return cleaned_data

    class Meta:
        model = models.AdditionalCode
        fields = ("type", "valid_between")


class AdditionalCodeCreateBaseForm(ValidityPeriodForm):
    class Meta:
        model = models.AdditionalCode
        fields = ("type", "code", "valid_between")

    type = forms.ModelChoiceField(
        label="Additional code type",
        help_text=(
            "Selecting the right additional code type will determine whether "
            "it can be associated with measures, commodity codes, or both"
        ),
        queryset=models.AdditionalCodeType.objects.latest_approved(),
        empty_label="Select an additional code type",
    )
    code = forms.CharField(
        label="Additional code ID",
        help_text=(
            "Must be 3 numeric characters and form a unique combination with "
            "the additional code type"
        ),
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        self.fields[
            "type"
        ].label_from_instance = lambda obj: f"{obj.sid} - {obj.description}"

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL


class AdditionalCodeCreateForm(AdditionalCodeCreateBaseForm):
    description = forms.CharField(
        label="Additional code description",
        help_text=(
            "You may enter HTML formatting if required. See the guide below "
            "for more information."
        ),
        widget=forms.Textarea,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper.layout = Layout(
            "type",
            Field.text("code", field_width=Fluid.ONE_QUARTER, maxlength="3"),
            "start_date",
            Field.textarea("description", rows=5),
            DescriptionHelpBox(),
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data["additional_code_description"] = models.AdditionalCodeDescription(
            description=cleaned_data.get("description"),
            validity_start=cleaned_data["valid_between"].lower,
        )
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        tx = WorkBasket.get_current_transaction(self.request)

        highest_sid = (
            models.AdditionalCode.objects.approved_up_to_transaction(tx).aggregate(
                Max("sid"),
            )["sid__max"]
        ) or 0
        instance.sid = highest_sid + 1

        if commit:
            instance.save(commit)
        return instance


class AdditionalCodeEditCreateForm(AdditionalCodeCreateBaseForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper.layout = Layout(
            "type",
            Field.text("code", field_width=Fluid.ONE_QUARTER, maxlength="3"),
            "start_date",
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )


class AdditionalCodeDescriptionForm(DescriptionForm):
    class Meta:
        model = models.AdditionalCodeDescription
        fields = DescriptionForm.Meta.fields


class AdditionalCodeCreateDescriptionForm(CreateDescriptionForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.layout.insert(
            0,
            Field(
                "described_additionalcode",
                type="hidden",
            ),
        )
        self.fields["description"].label = "Additional code description"

    class Meta:
        model = models.AdditionalCodeDescription
        fields = ("described_additionalcode", "description", "validity_start")


AdditionalCodeDeleteForm = delete_form_for(models.AdditionalCode)


AdditionalCodeDescriptionDeleteForm = delete_form_for(models.AdditionalCodeDescription)
