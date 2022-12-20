from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import HTML
from crispy_forms_gds.layout import Div
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Fluid
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms
from django.forms import ModelForm

from common.forms import DateInputFieldFixed
from common.forms import DescriptionHelpBox
from publishing import models


class LoadingReportForm(ModelForm):
    class Meta:
        model = models.LoadingReport
        fields = ("report_file", "comment")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            Field("report_file"),
            Field.textarea("comment", rows=5),
            HTML.warning("Submitting this form sends a notification email to users."),
            Submit(
                "submit",
                "Submit",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

        self.fields["report_file"].label = "Loading report file"
        self.fields["comment"].label = "Comments"


class PackagedWorkBasketCreateForm(ModelForm):
    class Meta:
        model = models.PackagedWorkBasket
        fields = ("theme", "description", "eif", "embargo", "jira_url")

    theme = forms.CharField(
        label="Theme",
        widget=forms.TextInput(attrs={"placeholder": "Updating"}),
        required=True,
    )

    description = forms.CharField(
        label="Note",
        help_text=(
            "Add your notes here. You may enter HTML formatting if required. "
            "See the guide below for more information."
        ),
        widget=forms.Textarea,
        required=False,
    )

    eif = DateInputFieldFixed(
        label="EIF date",
        help_text="For Example, 27 03 2008",
        required=False,
    )

    embargo = forms.CharField(
        label="Embargo",
        widget=forms.TextInput,
        required=False,
    )

    jira_url = forms.URLField(
        label="Tops Jira",
        help_text="Insert Tops Jira ticket link",
        widget=forms.TextInput,
        required=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            Field.text("theme", field_width=Fluid.TWO_THIRDS),
            Field.textarea("description", rows=5),
            DescriptionHelpBox(),
            Field("eif"),
            Field.text("embargo", field_width=Fluid.TWO_THIRDS),
            Field.text("jira_url", field_width=Fluid.TWO_THIRDS),
            Div(
                HTML(
                    '<span class="govuk-warning-text__icon" aria-hidden="true">!</span>',
                ),
                HTML(
                    '<strong class="govuk-warning-text__text">'
                    '<span class="govuk-warning-text__assistive">Warning</span>'
                    "The workbasket will be added to the queue ready to send to CDS."
                    "</strong>",
                ),
                css_class="govuk-warning-text",
            ),
            Submit(
                "submit",
                "Add to queue",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )
