from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import CreateView
from django.views.generic import UpdateView
from django.views.generic.edit import DeleteView

from reference_documents.forms.preferential_quota_suspension_forms import PreferentialQuotaSuspensionCreateUpdateForm, PreferentialQuotaSuspensionDeleteForm
from reference_documents.forms.preferential_quota_template_forms import PreferentialQuotaTemplateCreateUpdateForm, PreferentialQuotaTemplateDeleteForm
from reference_documents.models import PreferentialQuotaTemplate, PreferentialQuotaSuspension
from reference_documents.models import ReferenceDocumentVersion


class PreferentialQuotaSuspensionEdit(PermissionRequiredMixin, UpdateView):
    template_name = "reference_documents/preferential_quota_suspension/edit.jinja"
    permission_required = "reference_documents.change_preferentialquotasuspension"
    model = PreferentialQuotaSuspension
    form_class = PreferentialQuotaSuspensionCreateUpdateForm

    def get_success_url(self):
        return (
            reverse(
                "reference_documents:version-details",
                args=[
                    self.get_object().preferential_quota.preferential_quota_order_number.reference_document_version.pk,
                ],
            )
            + "#tariff-quotas"
        )

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["reference_document_version"] = (
            ReferenceDocumentVersion.objects.get(
                id=self.get_object().preferential_quota.preferential_quota_order_number.reference_document_version.pk,
            )
        )
        return context_data

    def get_form_kwargs(self):
        kwargs = super(PreferentialQuotaSuspensionEdit, self).get_form_kwargs()
        kwargs["reference_document_version"] = PreferentialQuotaSuspension.objects.get(
            id=self.kwargs["pk"],
        ).preferential_quota.preferential_quota_order_number.reference_document_version

        return kwargs


class PreferentialQuotaSuspensionCreate(PermissionRequiredMixin, CreateView):
    template_name = "reference_documents/preferential_quota_suspension/create.jinja"
    permission_required = "reference_documents.add_preferentialquotasuspension"
    model = PreferentialQuotaSuspension
    form_class = PreferentialQuotaSuspensionCreateUpdateForm

    def get_form_kwargs(self):
        kwargs = super(PreferentialQuotaSuspensionCreate, self).get_form_kwargs()
        kwargs["reference_document_version"] = ReferenceDocumentVersion.objects.get(
            id=self.kwargs["version_pk"],
        )

        # if "order_pk" in self.kwargs.keys():
        #     kwargs["preferential_quota_order_number"] = kwargs[
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
                id=self.kwargs["version_pk"],
            )
        )
        return context_data

    def get_success_url(self):
        return (
            reverse(
                "reference_documents:version-details",
                args=[
                    self.object.preferential_quota.preferential_quota_order_number.reference_document_version.pk,
                ],
            )
            + "#tariff-quotas"
        )


class PreferentialQuotaSuspensionDelete(PermissionRequiredMixin, DeleteView):
    form_class = PreferentialQuotaSuspensionDeleteForm
    template_name = "reference_documents/preferential_quota_suspension/delete.jinja"
    permission_required = "reference_documents.delete_preferentialquotasuspension"
    model = PreferentialQuotaSuspension

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
