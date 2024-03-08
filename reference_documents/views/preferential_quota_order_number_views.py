from django.contrib.auth.mixins import PermissionRequiredMixin
from django.urls import reverse
from django.views.generic import CreateView
from django.views.generic import UpdateView

from reference_documents.forms.preferential_quota_order_number_forms import (
    PreferentialQuotaOrderNumberCreateUpdateForm,
)
from reference_documents.models import PreferentialQuota
from reference_documents.models import ReferenceDocumentVersion


class PreferentialQuotaOrderNumberEditView(PermissionRequiredMixin, UpdateView):
    template_name = "reference_documents/preferential_quota_order_numbers/edit.jinja"
    permission_required = "reference_documents.edit_reference_document"
    model = PreferentialQuota
    form_class = PreferentialQuotaOrderNumberCreateUpdateForm

    def get_form_kwargs(self):
        kwargs = super(PreferentialQuotaOrderNumberEditView, self).get_form_kwargs()
        return kwargs

    def get_success_url(self):
        reverse(
            "reference_documents:version_details",
            args=[self.get_object().reference_document_version.pk],
        ) + "#tariff-quotas",


class PreferentialQuotaOrderNumberCreateView(PermissionRequiredMixin, CreateView):
    template_name = "reference_documents/preferential_quota_order_numbers/edit.jinja"
    permission_required = "reference_documents.edit_reference_document"
    model = PreferentialQuota
    form_class = PreferentialQuotaOrderNumberCreateUpdateForm

    def get_form_kwargs(self):
        kwargs = super(PreferentialQuotaOrderNumberCreateView, self).get_form_kwargs()
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
        return super(PreferentialQuotaOrderNumberCreateView, self).form_valid(form)

    def get_success_url(self):
        return (
            reverse(
                "reference_documents:version_details",
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


class PreferentialQuotaOrderNumberDeleteView(PermissionRequiredMixin, UpdateView):
    template_name = "preferential_quota_order_numbers/delete.jinja"
    permission_required = "reference_documents.edit_reference_document"
    model = PreferentialQuota
