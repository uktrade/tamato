from django.contrib.auth.mixins import PermissionRequiredMixin
from django.urls import reverse
from django.views.generic import CreateView
from django.views.generic import DeleteView
from django.views.generic import UpdateView

from reference_documents.forms.preferential_rate_forms import (
    PreferentialRateCreateUpdateForm,
)
from reference_documents.forms.preferential_rate_forms import PreferentialRateDeleteForm
from reference_documents.models import PreferentialRate
from reference_documents.models import ReferenceDocumentVersion


class PreferentialRateEdit(PermissionRequiredMixin, UpdateView):
    form_class = PreferentialRateCreateUpdateForm
    permission_required = "reference_documents.change_preferentialrate"
    model = PreferentialRate
    template_name = "reference_documents/preferential_rates/edit.jinja"

    def get_success_url(self):
        return reverse(
            "reference_documents:version-details",
            args=[self.object.reference_document_version.pk],
        )


class PreferentialRateCreate(PermissionRequiredMixin, CreateView):
    form_class = PreferentialRateCreateUpdateForm
    permission_required = "reference_documents.add_preferentialrate"
    model = PreferentialRate
    template_name = "reference_documents/preferential_rates/create.jinja"

    def get_success_url(self):
        return reverse(
            "reference_documents:version-details",
            args=[self.object.reference_document_version.pk],
        )

    def form_valid(self, form):
        instance = form.instance
        reference_document_version = ReferenceDocumentVersion.objects.get(
            pk=self.kwargs["version_pk"],
        )
        instance.order = len(reference_document_version.preferential_rates.all()) + 1
        instance.reference_document_version = reference_document_version
        form.save()
        return super(PreferentialRateCreate, self).form_valid(form)


class PreferentialRateDelete(PermissionRequiredMixin, DeleteView):
    template_name = "reference_documents/preferential_rates/delete.jinja"
    permission_required = "reference_documents.delete_preferentialrate"
    model = PreferentialRate
    form_class = PreferentialRateDeleteForm

    def get_success_url(self):
        return reverse(
            "reference_documents:version-details",
            args=[self.object.reference_document_version.pk],
        )
