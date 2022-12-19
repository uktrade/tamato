from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import HTML
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django.forms import ModelForm

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
