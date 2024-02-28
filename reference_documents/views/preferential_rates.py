from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import CreateView
from django.views.generic import DeleteView
from django.views.generic import UpdateView

from reference_documents.forms import PreferentialRateEditForm
from reference_documents.models import PreferentialRate
from reference_documents.models import ReferenceDocumentVersion


class PreferentialRateEditView(PermissionRequiredMixin, UpdateView):
    form_class = PreferentialRateEditForm
    permission_required = "reference_documents.edit_reference_document"
    model = PreferentialRate
    template_name = "reference_documents/preferential_rates/edit.jinja"

    def get_success_url(self):
        return reverse(
            "reference_documents:version_details",
            args=[self.object.reference_document_version.pk],
        )

    def form_valid(self, form):
        form.save()
        return super(PreferentialRateEditView, self).form_valid(form)


class PreferentialRateCreateView(PermissionRequiredMixin, CreateView):
    form_class = PreferentialRateEditForm
    permission_required = "reference_documents.edit_reference_document"
    model = PreferentialRate
    template_name = "reference_documents/preferential_rates/create.jinja"

    def get_success_url(self):
        return reverse(
            "reference_documents:version_details",
            args=[self.object.reference_document_version.pk],
        )

    def form_valid(self, form):
        instance = form.instance
        reference_document_version = ReferenceDocumentVersion.objects.get(
            pk=self.kwargs["pk"],
        )
        instance.order = len(reference_document_version.preferential_rates.all()) + 1
        instance.reference_document_version = reference_document_version
        form.save()
        return super(PreferentialRateCreateView, self).form_valid(form)


class PreferentialRateDeleteView(PermissionRequiredMixin, DeleteView):
    template_name = "reference_documents/preferential_rates/delete.jinja"
    permission_required = "reference_documents.edit_reference_document"
    model = PreferentialRate

    def get_success_url(self):
        return reverse(
            "reference_documents:version_details",
            args=[self.object.reference_document_version.pk],
        )

    def form_valid(self, form):
        instance = form.instance
        success_url = reverse(
            "reference_documents:version_details",
            args=[instance.reference_document_version.pk],
        )
        instance.delete()
        return HttpResponseRedirect(success_url)

    def post(self, request, *args, **kwargs):
        object = PreferentialRate.objects.all().get(pk=kwargs["pk"])
        success_url = reverse(
            "reference_documents:version_details",
            args=[object.reference_document_version.pk],
        )
        object.delete()
        return HttpResponseRedirect(success_url)
