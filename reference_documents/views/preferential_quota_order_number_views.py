from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import CreateView
from django.views.generic import DeleteView
from django.views.generic import UpdateView
from django.views.generic.edit import FormMixin

from reference_documents.forms.preferential_quota_order_number_forms import (
    PreferentialQuotaOrderNumberCreateUpdateForm,
)
from reference_documents.forms.preferential_quota_order_number_forms import (
    PreferentialQuotaOrderNumberDeleteForm,
)
from reference_documents.models import PreferentialQuotaOrderNumber
from reference_documents.models import ReferenceDocumentVersion


class PreferentialQuotaOrderNumberEdit(PermissionRequiredMixin, UpdateView):
    template_name = "reference_documents/preferential_quota_order_numbers/edit.jinja"
    permission_required = "reference_documents.edit_reference_document"
    model = PreferentialQuotaOrderNumber
    form_class = PreferentialQuotaOrderNumberCreateUpdateForm

    def get_form_kwargs(self):
        kwargs = super(PreferentialQuotaOrderNumberEdit, self).get_form_kwargs()
        kwargs["reference_document_version"] = PreferentialQuotaOrderNumber.objects.get(
            id=self.kwargs["pk"],
        ).reference_document_version
        return kwargs

    def get_success_url(self):
        return (
            reverse(
                "reference_documents:version-details",
                args=[self.get_object().reference_document_version.pk],
            )
            + "#tariff-quotas"
        )


class PreferentialQuotaOrderNumberCreate(PermissionRequiredMixin, CreateView):
    template_name = "reference_documents/preferential_quota_order_numbers/edit.jinja"
    permission_required = "reference_documents.edit_reference_document"
    model = PreferentialQuotaOrderNumber
    form_class = PreferentialQuotaOrderNumberCreateUpdateForm

    def get_form_kwargs(self):
        kwargs = super(PreferentialQuotaOrderNumberCreate, self).get_form_kwargs()
        kwargs["reference_document_version"] = ReferenceDocumentVersion.objects.get(
            id=self.kwargs["pk"],
        )

        return kwargs

    def form_valid(self, form):
        instance = form.instance
        reference_document_version = ReferenceDocumentVersion.objects.get(
            pk=self.kwargs["pk"],
        )
        instance.order = len(reference_document_version.preferential_rates.all()) + 1
        instance.reference_document_version = reference_document_version
        self.object = instance
        return super(PreferentialQuotaOrderNumberCreate, self).form_valid(form)

    def get_success_url(self):
        return (
            reverse(
                "reference_documents:version-details",
                args=[self.object.reference_document_version.pk],
            )
            + "#tariff-quotas"
        )


class PreferentialQuotaOrderNumberDelete(
    PermissionRequiredMixin,
    FormMixin,
    DeleteView,
):
    form_class = PreferentialQuotaOrderNumberDeleteForm
    template_name = "reference_documents/preferential_quota_order_numbers/delete.jinja"
    permission_required = "reference_documents.edit_reference_document"
    model = PreferentialQuotaOrderNumber

    def get_success_url(self) -> str:
        return reverse(
            "reference_documents:version-details",
            kwargs={"pk": self.kwargs["version_pk"]},
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.get_object()
        return kwargs

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            self.request.session["deleted_version"] = {
                "quota_order_number": f"{self.object.quota_order_number}",
            }
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        self.object.delete()
        return redirect(self.get_success_url())
