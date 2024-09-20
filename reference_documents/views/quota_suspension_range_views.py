from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import CreateView
from django.views.generic import UpdateView
from django.views.generic.edit import DeleteView

from reference_documents.forms.ref_quota_suspension_range_forms import (
    RefQuotaSuspensionRangeCreateUpdateForm,
)
from reference_documents.forms.ref_quota_suspension_range_forms import (
    RefQuotaSuspensionRangeDeleteForm,
)
from reference_documents.models import ReferenceDocumentVersion
from reference_documents.models import RefQuotaSuspensionRange


class RefQuotaSuspensionRangeEdit(PermissionRequiredMixin, UpdateView):
    template_name = "reference_documents/ref_quota_suspension_ranges/edit.jinja"
    permission_required = "reference_documents.change_refquotasuspension"
    model = RefQuotaSuspensionRange
    form_class = RefQuotaSuspensionRangeCreateUpdateForm

    def get_success_url(self):
        return (
            reverse(
                "reference_documents:version-details",
                args=[
                    self.get_object().ref_quota_definition_range.ref_order_number.reference_document_version.pk,
                ],
            )
            + "#tariff-quotas"
        )

    def get_form_kwargs(self):
        kwargs = super(RefQuotaSuspensionRangeEdit, self).get_form_kwargs()
        kwargs["reference_document_version"] = RefQuotaSuspensionRange.objects.get(
            id=self.kwargs["pk"],
        ).ref_quota_definition_range.ref_order_number.reference_document_version
        kwargs["ref_order_number"] = RefQuotaSuspensionRange.objects.get(
            id=self.kwargs["pk"],
        ).ref_quota_definition_range.ref_order_number
        kwargs["ref_quota_definition_range"] = RefQuotaSuspensionRange.objects.get(
            id=self.kwargs["pk"],
        ).ref_quota_definition_range
        return kwargs


class RefQuotaSuspensionRangeCreate(PermissionRequiredMixin, CreateView):
    template_name = "reference_documents/ref_quota_suspension_ranges/create.jinja"
    permission_required = "reference_documents.add_refquotasuspension"
    model = RefQuotaSuspensionRange
    form_class = RefQuotaSuspensionRangeCreateUpdateForm

    def get_form_kwargs(self):
        kwargs = super(RefQuotaSuspensionRangeCreate, self).get_form_kwargs()
        kwargs["reference_document_version"] = ReferenceDocumentVersion.objects.get(
            id=self.kwargs["version_pk"],
        )
        kwargs["ref_order_number"] = None
        kwargs["ref_quota_definition_range"] = None

        return kwargs

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["reference_document_version"] = (
            ReferenceDocumentVersion.objects.get(
                id=self.kwargs["version_pk"],
            )
        )
        return context_data

    def form_valid(self, form):
        form.instance.order = 1
        form.save()
        return super(RefQuotaSuspensionRangeCreate, self).form_valid(form)

    def get_success_url(self):
        return (
            reverse(
                "reference_documents:version-details",
                args=[
                    self.object.ref_quota_definition_range.ref_order_number.reference_document_version.pk,
                ],
            )
            + "#tariff-quotas"
        )


class RefQuotaSuspensionRangeDelete(PermissionRequiredMixin, DeleteView):
    form_class = RefQuotaSuspensionRangeDeleteForm
    template_name = "reference_documents/ref_quota_suspension_ranges/delete.jinja"
    permission_required = "reference_documents.delete_refquotasuspension"
    model = RefQuotaSuspensionRange

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
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        self.object.delete()
        return redirect(self.get_success_url())
