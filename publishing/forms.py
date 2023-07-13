from typing import List

from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import HTML
from crispy_forms_gds.layout import Div
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Fluid
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms
from django.conf import settings
from django.forms import ModelForm
from django_chunk_upload_handlers.clam_av import validate_virus_check_result

from common.forms import DateInputFieldFixed
from common.forms import DescriptionHelpBox
from common.forms import MultipleFileField
from common.util import get_mime_type
from publishing.models import LoadingReport
from publishing.models import PackagedWorkBasket


class LoadingReportForm(ModelForm):
    class Meta:
        model = LoadingReport
        fields = ("comments",)

    files = MultipleFileField()

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            Field("files", css_class="govuk-file-upload"),
            Field.textarea("comments", rows=5),
            HTML.warning("Upon submission, DBT and HMRC will be notified."),
            Submit(
                "submit",
                "Submit",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

        self.fields["files"].label = "Loading report files"
        self.fields["comments"].label = "Comments"

    def clean_files(self):
        files = self.request.FILES.getlist("files", None)
        url_path = self.request.path.rsplit("/")[-3]

        if not files and url_path == "reject" and not self.request.user.is_superuser:
            raise forms.ValidationError("Select a loading report")

        if files and len(files) > 10:
            raise forms.ValidationError(
                "You can only select up to 10 loading report files",
            )

        for file in files:
            validate_virus_check_result(file)

            mime_type = get_mime_type(file)
            if mime_type not in ["text/html", "application/html"]:
                raise forms.ValidationError(
                    "The selected loading report files must be HTML",
                )

            if (
                file.size
                > settings.MAX_LOADING_REPORT_FILE_SIZE_MEGABYTES * 1024 * 1024
            ):
                raise forms.ValidationError(
                    f"Report file exceeds {settings.MAX_LOADING_REPORT_FILE_SIZE_MEGABYTES} "
                    f"megabytes maximum file size.",
                )

        return files

    def save(self, packaged_workbasket: PackagedWorkBasket) -> List[LoadingReport]:
        """Use form data to create LoadingReport instance(s) associated with the
        packaged workbasket."""
        files = self.cleaned_data["files"]
        if not files:
            loading_report = LoadingReport.objects.create(
                comments=self.cleaned_data["comments"],
                packaged_workbasket=packaged_workbasket,
            )
            return [loading_report]

        instances = [
            LoadingReport(
                file=file,
                file_name=file.name,
                comments=self.cleaned_data["comments"],
                packaged_workbasket=packaged_workbasket,
            )
            for file in files
        ]
        loading_reports = LoadingReport.objects.bulk_create(instances)
        return loading_reports


class PackagedWorkBasketCreateForm(forms.ModelForm):
    class Meta:
        model = PackagedWorkBasket
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
                    "The workbasket will be added to the packaging queue to send to CDS."
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
