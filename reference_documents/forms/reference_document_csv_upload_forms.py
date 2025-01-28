from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms
from django.core.exceptions import ValidationError

from reference_documents.models import CSVUpload
from reference_documents.tasks import import_reference_document_data


class ReferenceDocumentCreateCsvUploadForm(forms.ModelForm):
    preferential_rates_csv_data = forms.FileField(required=False)
    order_number_csv_data = forms.FileField(required=False)
    quota_definition_csv_data = forms.FileField(required=False)

    class Meta:
        model = CSVUpload
        fields = [
            "preferential_rates_csv_data",
            "order_number_csv_data",
            "quota_definition_csv_data",
        ]

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            "preferential_rates_csv_data",
            "order_number_csv_data",
            "quota_definition_csv_data",
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    def clean(self):
        pass

        # check at least one file has been uploaded
        check_fields = [
            "preferential_rates_csv_data",
            "order_number_csv_data",
            "quota_definition_csv_data",
        ]

        at_least_one = False
        for field in check_fields:
            if field in self.cleaned_data.keys():
                at_least_one = True

        if not at_least_one:
            self.add_error(
                "preferential_rates_csv_data",
                "Upload at least one CSV file in any of the file fields",
            )

        if len(self.errors):
            raise forms.ValidationError(" & ".join(self.errors))

    def clean_preferential_rates_csv_data(self):
        expected_headers = [
            "comm_code",
            "rate",
            "validity_start",
            "validity_end",
            "area_id",
            "document_version",
        ]
        if self.cleaned_data.get("preferential_rates_csv_data"):
            headers = (
                self.cleaned_data.get("preferential_rates_csv_data")
                .file.readline()
                .decode("utf-8")
            )
            headers_list = headers.strip().split(",")
            if headers_list == expected_headers:
                return headers + self.cleaned_data.get(
                    "preferential_rates_csv_data",
                ).file.read().decode("utf-8")
            else:
                raise ValidationError(
                    f"Headers not correct, expected {expected_headers} got {headers_list}",
                )

    def clean_order_number_csv_data(self):
        expected_headers = [
            "order_number",
            "validity_start",
            "validity_end",
            "parent_order_number",
            "coefficient",
            "relationship_type",
            "area_id",
            "document_version",
        ]
        if self.cleaned_data.get("order_number_csv_data"):
            headers = (
                self.cleaned_data.get("order_number_csv_data")
                .file.readline()
                .decode("utf-8")
            )
            headers_list = headers.strip().split(",")
            if headers_list == expected_headers:
                return headers + self.cleaned_data.get(
                    "order_number_csv_data",
                ).file.read().decode("utf-8")
            else:
                raise ValidationError(
                    f"Headers not correct, expected {expected_headers} got {headers_list}",
                )

    def clean_quota_definition_csv_data(self):
        expected_headers = [
            "order_number",
            "comm_code",
            "duty_rate",
            "initial_volume",
            "measurement",
            "validity_start",
            "validity_end",
            "area_id",
            "document_version",
        ]
        if self.cleaned_data.get("quota_definition_csv_data"):
            headers = (
                self.cleaned_data.get("quota_definition_csv_data")
                .file.readline()
                .decode("utf-8")
            )
            headers_list = headers.strip().split(",")
            if headers_list == expected_headers:
                return headers + self.cleaned_data.get(
                    "quota_definition_csv_data",
                ).file.read().decode("utf-8")
            else:
                raise ValidationError(
                    f"Headers not correct, expected {expected_headers} got {headers_list}",
                )

    def save(self, **kwargs):
        self.instance.save()
        import_reference_document_data.delay(self.instance.pk)
        return
