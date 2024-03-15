from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import CreateView
from django.views.generic import UpdateView
from django.views.generic.edit import DeleteView
from django.views.generic.edit import FormMixin

from reference_documents.forms.preferential_quota_forms import (
    PreferentialQuotaBulkCreate,
)
from reference_documents.forms.preferential_quota_forms import (
    PreferentialQuotaCreateUpdateForm,
)
from reference_documents.forms.preferential_quota_forms import (
    PreferentialQuotaDeleteForm,
)
from reference_documents.models import PreferentialQuota
from reference_documents.models import ReferenceDocumentVersion


class PreferentialQuotaEditView(PermissionRequiredMixin, UpdateView):
    template_name = "reference_documents/preferential_quotas/edit.jinja"
    permission_required = "reference_documents.edit_reference_document"
    model = PreferentialQuota
    form_class = PreferentialQuotaCreateUpdateForm

    def get_form_kwargs(self):
        kwargs = super(PreferentialQuotaEditView, self).get_form_kwargs()
        kwargs["reference_document_version"] = PreferentialQuota.objects.get(
            id=self.kwargs["pk"],
        ).preferential_quota_order_number.reference_document_version
        kwargs["preferential_quota_order_number"] = PreferentialQuota.objects.get(
            id=self.kwargs["pk"],
        ).preferential_quota_order_number
        return kwargs

    def post(self, request, *args, **kwargs):
        quota = self.get_object()
        quota.save()
        return redirect(
            reverse(
                "reference_documents:version-details",
                args=[
                    quota.preferential_quota_order_number.reference_document_version.pk,
                ],
            )
            + "#tariff-quotas",
        )


class PreferentialQuotaCreateView(PermissionRequiredMixin, CreateView):
    template_name = "reference_documents/preferential_quotas/create.jinja"
    permission_required = "reference_documents.edit_reference_document"
    model = PreferentialQuota
    form_class = PreferentialQuotaCreateUpdateForm

    def get_form_kwargs(self):
        kwargs = super(PreferentialQuotaCreateView, self).get_form_kwargs()
        kwargs["reference_document_version"] = ReferenceDocumentVersion.objects.get(
            id=self.kwargs["version_pk"],
        )

        if "order_pk" in self.kwargs.keys():
            kwargs["preferential_quota_order_number"] = kwargs[
                "reference_document_version"
            ].preferential_quota_order_numbers.get(
                id=self.kwargs["order_pk"],
            )
        else:
            kwargs["preferential_quota_order_number"] = None

        return kwargs

    def form_valid(self, form):
        instance = form.instance
        reference_document_version = ReferenceDocumentVersion.objects.get(
            pk=self.kwargs["version_pk"],
        )
        instance.order = len(reference_document_version.preferential_rates.all()) + 1
        instance.reference_document_version = reference_document_version
        self.object = instance
        return super(PreferentialQuotaCreateView, self).form_valid(form)

    def get_success_url(self):
        return (
            reverse(
                "reference_documents:version-details",
                args=[self.object.reference_document_version.pk],
            )
            + "#tariff-quotas"
        )


class PreferentialQuotaBulkCreateView(PermissionRequiredMixin, CreateView):
    template_name = "reference_documents/preferential_quotas/bulk_create.jinja"
    permission_required = "reference_documents.add_preferentialquota"
    model = PreferentialQuota
    form_class = PreferentialQuotaBulkCreate
    queryset = ReferenceDocumentVersion.objects.all()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        print(f"get object: {self.get_object()}")
        kwargs["reference_document_version"] = self.get_object()
        return kwargs

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data[
            "reference_document_version"
        ] = ReferenceDocumentVersion.objects.all().get(
            pk=self.kwargs["pk"],
        )
        return context_data

    def form_valid(self, form):
        instance = form.instance
        reference_document_version = ReferenceDocumentVersion.objects.get(
            pk=self.kwargs["pk"],
        )
        instance.order = len(reference_document_version.preferential_rates.all()) + 1
        instance.reference_document_version = reference_document_version
        self.object = instance
        self.object = form.save()
        return redirect(self.get_success_url())

    def get_success_url(self):
        return (
            reverse(
                "reference_documents:version-details",
                args=[self.object.reference_document_version.pk],
            )
            + "#tariff-quotas"
        )


class PreferentialQuotaDeleteView(PermissionRequiredMixin, FormMixin, DeleteView):
    form_class = PreferentialQuotaDeleteForm
    template_name = "reference_documents/preferential_quotas/delete.jinja"
    permission_required = "reference_documents.edit_reference_document"
    model = PreferentialQuota

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
