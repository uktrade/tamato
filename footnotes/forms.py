from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Fixed
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms

from common.forms import CreateDescriptionForm
from common.forms import DescriptionForm
from common.forms import DescriptionHelpBox
from common.forms import ValidityPeriodForm
from common.forms import delete_form_for
from common.util import get_next_id
from footnotes import models
from workbaskets.models import WorkBasket


class FootnoteForm(ValidityPeriodForm):
    code = forms.CharField(
        label="Footnote ID",
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields[
            "footnote_type"
        ].label_from_instance = (
            lambda obj: f"{obj.footnote_type_id} - {obj.description}"
        )
        self.fields["footnote_type"].label = "Footnote type"
        self.fields["footnote_type"].required = False

        if self.instance.pk:
            self.fields["code"].disabled = True
            self.fields["code"].help_text = "You can't edit this"
            self.fields["code"].initial = str(self.instance)

            self.fields["footnote_type"].disabled = True
            self.fields["footnote_type"].help_text = "You can't edit this"

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL

        self.helper.layout = Layout(
            Field.text(
                "code",
                field_width=Fixed.TEN,
            ),
            Field("footnote_type"),
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

        if self.instance.pk and self.instance.footnote_id:
            cleaned_data["footnote_id"] = self.instance.footnote_id

        # get type from instance if not submitted
        footnote_type = cleaned_data.get("footnote_type")

        if not footnote_type and self.instance.pk and self.instance.footnote_type:
            footnote_type = self.instance.footnote_type

        if not footnote_type:
            self.add_error("footnote_type", "Footnote type is required")

        return cleaned_data

    class Meta:
        model = models.Footnote
        fields = ("footnote_type", "valid_between")


class FootnoteCreateForm(ValidityPeriodForm):

    footnote_type = forms.ModelChoiceField(
        label="Footnote type",
        help_text="Selecting the right footnote type will determine whether it can be associated with measures, commodity codes, or both",
        queryset=models.FootnoteType.objects.latest_approved(),
        empty_label="Select a footnote type",
    )

    description = forms.CharField(
        label="Footnote description",
        help_text="You may enter HTML formatting if required. See the guide below for more information.",
        widget=forms.Textarea,
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        self.fields[
            "footnote_type"
        ].label_from_instance = (
            lambda obj: f"{obj.footnote_type_id} - {obj.description}"
        )

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            "footnote_type",
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

        if self.errors:
            return cleaned_data

        cleaned_data["footnote_description"] = models.FootnoteDescription(
            description=cleaned_data["description"],
            validity_start=cleaned_data["valid_between"].lower,
        )

        return cleaned_data

    def save(self, commit=True):
        instance = super(FootnoteCreateForm, self).save(commit=False)

        workbasket = WorkBasket.current(self.request)
        tx = None
        if workbasket:
            tx = workbasket.transactions.order_by("order").last()

        instance.footnote_id = get_next_id(
            models.Footnote.objects.filter(
                footnote_type__footnote_type_id=instance.footnote_type.footnote_type_id,
            ).approved_up_to_transaction(tx),
            instance._meta.get_field("footnote_id"),
            max_len=3,
        )
        if commit:
            instance.save()
        return instance

    class Meta:
        model = models.Footnote
        fields = ("footnote_type", "valid_between")


class FootnoteDescriptionForm(DescriptionForm):
    class Meta:
        model = models.FootnoteDescription
        fields = DescriptionForm.Meta.fields


class FootnoteCreateDescriptionForm(CreateDescriptionForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper.layout.insert(
            0,
            Field(
                "described_footnote",
                type="hidden",
            ),
        )
        self.fields["description"].label = "Footnote description"

    class Meta:
        model = models.FootnoteDescription
        fields = ("described_footnote", "description", "validity_start")


FootnoteDeleteForm = delete_form_for(models.Footnote)
FootnoteDescriptionDeleteForm = delete_form_for(models.FootnoteDescription)
