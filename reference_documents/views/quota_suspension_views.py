from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import CreateView
from django.views.generic import UpdateView
from django.views.generic.edit import DeleteView

from reference_documents.forms.ref_quota_suspension_forms import RefQuotaSuspensionCreateUpdateForm, RefQuotaSuspensionDeleteForm
from reference_documents.models import RefQuotaSuspension
from reference_documents.models import ReferenceDocumentVersion


class RefQuotaSuspensionEdit(PermissionRequiredMixin, UpdateView):
    template_name = "reference_documents/ref_quota_suspensions/edit.jinja"
    permission_required = "reference_documents.change_refquotasuspension"
    model = RefQuotaSuspension
    form_class = RefQuotaSuspensionCreateUpdateForm

    def get_success_url(self):
        return (
            reverse(
                "reference_documents:version-details",
                args=[
                    self.get_object().ref_quota_definition.ref_order_number.reference_document_version.pk,
                ],
            )
            + "#tariff-quotas"
        )

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["reference_document_version"] = (
            ReferenceDocumentVersion.objects.get(
                id=self.get_object().ref_quota_definition.ref_order_number.reference_document_version.pk,
            )
        )
        return context_data

    def get_form_kwargs(self):
        kwargs = super(RefQuotaSuspensionEdit, self).get_form_kwargs()
        kwargs["reference_document_version"] = RefQuotaSuspension.objects.get(
            id=self.kwargs["pk"],
        ).ref_quota_definition.ref_order_number.reference_document_version

        return kwargs


class RefQuotaSuspensionCreate(PermissionRequiredMixin, CreateView):
    template_name = "reference_documents/ref_quota_suspensions/create.jinja"
    permission_required = "reference_documents.add_refquotasuspension"
    model = RefQuotaSuspension
    form_class = RefQuotaSuspensionCreateUpdateForm

    def get_form_kwargs(self):
        kwargs = super(RefQuotaSuspensionCreate, self).get_form_kwargs()
        kwargs["reference_document_version"] = ReferenceDocumentVersion.objects.get(
            id=self.kwargs["pk"],
        )

        # if "order_pk" in self.kwargs.keys():
        #     kwargs["ref_order_number"] = kwargs[
        #         "reference_document_version"
        #     ].preferential_quota_order_numbers.get(
        #         id=self.kwargs["order_pk"],
        #     )
        # else:
        #     kwargs["preferential_quota_order_number"] = None

        return kwargs

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["reference_document_version"] = (
            ReferenceDocumentVersion.objects.get(
                id=self.kwargs["pk"],
            )
        )
        return context_data

    def get_success_url(self):
        return (
            reverse(
                "reference_documents:version-details",
                args=[
                    self.object.ref_quota_definition.ref_order_number.reference_document_version.pk,
                ],
            )
            + "#tariff-quotas"
        )


class RefQuotaSuspensionDelete(PermissionRequiredMixin, DeleteView):
    form_class = RefQuotaSuspensionDeleteForm
    template_name = "reference_documents/ref_quota_suspensions/delete.jinja"
    permission_required = "reference_documents.delete_refquotasuspension"
    model = RefQuotaSuspension

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
