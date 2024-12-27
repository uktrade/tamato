from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponseRedirect
from django.views.generic import CreateView
from django.views.generic import DetailView
from django.views.generic import ListView
from django.views.generic import TemplateView

from common.views import WithPaginationListMixin
from reference_documents.forms.reference_document_csv_upload_forms import (
    ReferenceDocumentCreateCsvUploadForm,
)
from reference_documents.models import CSVUpload


class ReferenceDocumentCsvUploadContext:

    def __init__(self, object_list):
        self.object_list = object_list

    def headers(self):
        return [
            {"text": "Date and time uploaded"},
            {"text": "status"},
            {"text": "CSV data for"},
            {"text": "Actions"},
        ]

    def rows(self):
        csv_uploads = []
        for csv_upload in self.object_list:
            actions = f'<a href="/reference_documents/csv_uploads/{csv_upload.id}">Details</a><br>'

            csv_uploads.append(
                [
                    {
                        "text": csv_upload.created_at.strftime("%Y/%m/%d, %H:%M:%S"),
                    },
                    {
                        "text": f"{csv_upload.status}",
                    },
                    {
                        "text": f"{csv_upload.csv_content_types()}",
                    },
                    {
                        "html": actions,
                    },
                ],
            )
        return csv_uploads

    def get_context(self):
        return {
            "reference_documents": self.rows(),
            "reference_document_headers": self.headers(),
        }


class ReferenceDocumentCsvUploadList(
    PermissionRequiredMixin,
    WithPaginationListMixin,
    ListView,
):
    template_name = "reference_documents/reference_document_csv_upload/index.jinja"
    permission_required = "reference_documents.view_csvupload"
    model = CSVUpload
    paginate_by = 20

    def get_queryset(self):
        return CSVUpload.objects.all().order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            ReferenceDocumentCsvUploadContext(
                context["object_list"],
            ).get_context(),
        )
        return context


class ReferenceDocumentCsvUploadDetails(PermissionRequiredMixin, DetailView):
    template_name = "reference_documents/reference_document_csv_upload/details.jinja"
    permission_required = "reference_documents.view_csvupload"
    model = CSVUpload


class ReferenceDocumentCsvUploadCreate(PermissionRequiredMixin, CreateView):
    template_name = "reference_documents/reference_document_csv_upload/create.jinja"
    permission_required = "reference_documents.add_csvupload"
    form_class = ReferenceDocumentCreateCsvUploadForm
    success_url = "/reference_documents/csv_upload_succeeded/"

    def form_valid(self, form):
        # read files to string
        form.save()
        return HttpResponseRedirect(self.success_url)


class ReferenceDocumentCsvUploadCreateSuccess(PermissionRequiredMixin, TemplateView):
    template_name = (
        "reference_documents/reference_document_csv_upload/create_success.jinja"
    )
    permission_required = "reference_documents.add_csvupload"
