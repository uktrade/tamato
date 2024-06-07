from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import CreateView
from django.views.generic import UpdateView
from django.views.generic.edit import DeleteView

from reference_documents.forms.preferential_quota_suspension_template_forms import PreferentialQuotaSuspensionTemplateCreateUpdateForm, PreferentialQuotaSuspensionTemplateDeleteForm
from reference_documents.forms.preferential_quota_template_forms import PreferentialQuotaTemplateCreateUpdateForm, PreferentialQuotaTemplateDeleteForm
from reference_documents.models import PreferentialQuotaTemplate, PreferentialQuotaSuspensionTemplate
from reference_documents.models import ReferenceDocumentVersion


class PreferentialQuotaSuspensionTemplateEdit(PermissionRequiredMixin, UpdateView):
    template_name = "reference_documents/preferential_quota_suspension_template/edit.jinja"
    permission_required = "reference_documents.change_preferentialquotasuspension"
    model = PreferentialQuotaSuspensionTemplate
    form_class = PreferentialQuotaSuspensionTemplateCreateUpdateForm

    def get_success_url(self):
        return (
            reverse(
                "reference_documents:version-details",
                args=[
                    self.get_object().preferential_quota_order_number.reference_document_version.pk,
                ],
            )
            + "#tariff-quotas"
        )

    def get_form_kwargs(self):
        kwargs = super(PreferentialQuotaSuspensionTemplateEdit, self).get_form_kwargs()
        kwargs["reference_document_version"] = PreferentialQuotaSuspensionTemplate.objects.get(
            id=self.kwargs["pk"],
        ).preferential_quota_template.preferential_quota_order_number.reference_document_version
        kwargs["preferential_quota_order_number"] = PreferentialQuotaSuspensionTemplate.objects.get(
            id=self.kwargs["pk"],
        ).preferential_quota_template.preferential_quota_order_number
        return kwargs


class PreferentialQuotaSuspensionTemplateCreate(PermissionRequiredMixin, CreateView):
    template_name = "reference_documents/preferential_quota_suspension_template/create.jinja"
    permission_required = "reference_documents.add_preferentialquotasuspension"
    model = PreferentialQuotaSuspensionTemplate
    form_class = PreferentialQuotaSuspensionTemplateCreateUpdateForm

    def get_form_kwargs(self):
        kwargs = super(PreferentialQuotaSuspensionTemplateCreate, self).get_form_kwargs()
        kwargs["reference_document_version"] = ReferenceDocumentVersion.objects.get(
            id=self.kwargs["version_pk"],
        )

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
        return super(PreferentialQuotaSuspensionTemplateCreate, self).form_valid(form)

    def get_success_url(self):
        return (
            reverse(
                "reference_documents:version-details",
                args=[
                    self.object.preferential_quota_order_number.reference_document_version.pk,
                ],
            )
            + "#tariff-quotas"
        )


class PreferentialQuotaSuspensionTemplateDelete(PermissionRequiredMixin, DeleteView):
    form_class = PreferentialQuotaSuspensionTemplateDeleteForm
    template_name = "reference_documents/preferential_quota_suspension_template/delete.jinja"
    permission_required = "reference_documents.delete_preferentialquotasuspension"
    model = PreferentialQuotaSuspensionTemplate

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
                "quota_commodity_code": f"{self.object.commodity_code}",
            }
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        self.object.delete()
        return redirect(self.get_success_url())
