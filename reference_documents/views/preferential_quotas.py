from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import UpdateView

from reference_documents.forms import PreferentialQuotaCreateUpdateForm
from reference_documents.models import PreferentialQuota


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


class PreferentialQuotaDeleteView(PermissionRequiredMixin, UpdateView):
    template_name = "preferential_quotas/delete.jinja"
    permission_required = "reference_documents.edit_reference_document"
    model = PreferentialQuota
