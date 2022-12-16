from crispy_forms_gds.helper import FormHelper
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
            Submit(
                "submit",
                "Submit",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )
