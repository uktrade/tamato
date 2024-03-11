from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import CreateView
from django.views.generic import UpdateView

from reference_documents.forms.preferential_quota_forms import (
    PreferentialQuotaBulkCreate,
)
from reference_documents.forms.preferential_quota_forms import (
    PreferentialQuotaCreateUpdateForm,
)
from reference_documents.models import PreferentialQuota
from reference_documents.models import ReferenceDocumentVersion


class PreferentialQuotaEditView(PermissionRequiredMixin, UpdateView):
    template_name = "reference_documents/preferential_quotas/edit.jinja"
    permission_required = "reference_documents.edit_reference_document"
    model = PreferentialQuota
    form_class = PreferentialQuotaCreateUpdateForm

    def post(self, request, *args, **kwargs):
        quota = self.get_object()
        quota.save()
        return redirect(
            reverse(
                "reference_documents:version_details",
                args=[quota.reference_document_version.pk],
            )
            + "#tariff-quotas",
        )


class PreferentialQuotaCreateView(PermissionRequiredMixin, CreateView):
    template_name = "reference_documents/preferential_quotas/edit.jinja"
    permission_required = "reference_documents.edit_reference_document"
    model = PreferentialQuota
    form_class = PreferentialQuotaCreateUpdateForm

    def form_valid(self, form):
        instance = form.instance
        reference_document_version = ReferenceDocumentVersion.objects.get(
            pk=self.kwargs["pk"],
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

    # def post(self, request, *args, **kwargs):
    #     quota = self.get_object()
    #     quota.save()
    #     return redirect(
    #         reverse(
    #             "reference_documents:version_details",
    #             args=[quota.reference_document_version.pk],
    #         )
    #         + "#tariff-quotas",
    #     )


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


class PreferentialQuotaDeleteView(PermissionRequiredMixin, UpdateView):
    template_name = "preferential_quotas/delete.jinja"
    permission_required = "reference_documents.edit_reference_document"
    model = PreferentialQuota
