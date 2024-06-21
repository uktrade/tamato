from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import CreateView
from django.views.generic import DeleteView
from django.views.generic import FormView
from django.views.generic import UpdateView

from reference_documents.forms.ref_rate_forms import (
    RefRateCreateUpdateForm,
    RefRateDeleteForm,
    RefRateBulkCreateForm
)

from reference_documents.models import RefRate
from reference_documents.models import ReferenceDocumentVersion


class RefRateEdit(PermissionRequiredMixin, UpdateView):
    form_class = RefRateCreateUpdateForm
    permission_required = "reference_documents.change_refrate"
    model = RefRate
    template_name = "reference_documents/ref_rates/edit.jinja"

    def get_success_url(self):
        return reverse(
            "reference_documents:version-details",
            args=[self.object.reference_document_version.pk],
        )


class RefRateCreate(PermissionRequiredMixin, CreateView):
    form_class = RefRateCreateUpdateForm
    permission_required = "reference_documents.add_refrate"
    model = RefRate
    template_name = "reference_documents/ref_rates/create.jinja"

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
        instance.reference_document_version = reference_document_version
        form.save()
        return super(RefRateCreate, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["reference_document_version"] = (
            ReferenceDocumentVersion.objects.get(
                id=self.kwargs["version_pk"],
            )
        )
        return context_data


class RefRateDelete(PermissionRequiredMixin, DeleteView):
    template_name = "reference_documents/ref_rates/delete.jinja"
    permission_required = "reference_documents.delete_refrate"
    model = RefRate
    form_class = RefRateDeleteForm

    def get_success_url(self):
        return reverse(
            "reference_documents:version-details",
            args=[self.object.reference_document_version.pk],
        )


class RefRateBulkCreate(PermissionRequiredMixin, FormView):
    template_name = "reference_documents/ref_rates/bulk_create.jinja"
    permission_required = "reference_documents.add_refrate"
    form_class = RefRateBulkCreateForm
    queryset = ReferenceDocumentVersion.objects.all()

    def get_reference_document_version(self):
        return ReferenceDocumentVersion.objects.all().get(
            pk=self.kwargs["pk"],
        )

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["reference_document_version"] = (
            self.get_reference_document_version()
        )
        return context_data

    def form_valid(self, form):
        cleaned_data = form.cleaned_data
        commodity_codes = set(form.cleaned_data["commodity_codes"].splitlines())
        for commodity_code in commodity_codes:
            RefRate.objects.create(
                commodity_code=commodity_code,
                duty_rate=cleaned_data["duty_rate"],
                valid_between=cleaned_data[f"valid_between"],
                reference_document_version=self.get_reference_document_version(),
            )
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse(
            "reference_documents:version-details",
            args=[self.get_reference_document_version().pk],
        )
