from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import CreateView
from django.views.generic import UpdateView
from django.views.generic.edit import DeleteView
from reference_documents.forms.ref_quota_definition_range_forms import RefQuotaDefinitionRangeCreateUpdateForm, RefQuotaDefinitionRangeDeleteForm
from reference_documents.models import RefQuotaDefinitionRange
from reference_documents.models import ReferenceDocumentVersion


class RefQuotaDefinitionRangeEdit(PermissionRequiredMixin, UpdateView):
    template_name = "reference_documents/ref_quota_definition_ranges/edit.jinja"
    permission_required = "reference_documents.change_refquotadefinitionrange"
    model = RefQuotaDefinitionRange
    form_class = RefQuotaDefinitionRangeCreateUpdateForm

    def get_success_url(self):
        return (
            reverse(
                "reference_documents:version-details",
                args=[
                    self.get_object().ref_order_number.reference_document_version.pk,
                ],
            )
            + "#tariff-quotas"
        )

    def get_form_kwargs(self):
        kwargs = super(RefQuotaDefinitionRangeEdit, self).get_form_kwargs()
        kwargs["reference_document_version"] = RefQuotaDefinitionRange.objects.get(
            id=self.kwargs["pk"],
        ).ref_order_number.reference_document_version
        kwargs["ref_order_number"] = RefQuotaDefinitionRange.objects.get(
            id=self.kwargs["pk"],
        ).ref_order_number
        return kwargs


class RefQuotaDefinitionRangeCreate(PermissionRequiredMixin, CreateView):
    template_name = "reference_documents/ref_quota_definition_ranges/create.jinja"
    permission_required = "reference_documents.add_refquotadefinitionrange"
    model = RefQuotaDefinitionRange
    form_class = RefQuotaDefinitionRangeCreateUpdateForm

    def get_form_kwargs(self):
        kwargs = super(RefQuotaDefinitionRangeCreate, self).get_form_kwargs()
        kwargs["reference_document_version"] = ReferenceDocumentVersion.objects.get(
            id=self.kwargs["version_pk"],
        )

        if "order_pk" in self.kwargs.keys():
            kwargs["ref_order_number"] = kwargs[
                "reference_document_version"
            ].ref_order_number.get(
                id=self.kwargs["order_pk"],
            )
        else:
            kwargs["ref_order_number"] = None

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
        return super(RefQuotaDefinitionRangeCreate, self).form_valid(form)

    def get_success_url(self):
        return (
            reverse(
                "reference_documents:version-details",
                args=[
                    self.object.ref_order_number.reference_document_version.pk,
                ],
            )
            + "#tariff-quotas"
        )


class RefQuotaDefinitionRangeDelete(PermissionRequiredMixin, DeleteView):
    form_class = RefQuotaDefinitionRangeDeleteForm
    template_name = "reference_documents/ref_quota_definition_ranges/delete.jinja"
    permission_required = "reference_documents.delete_preferentialquotatemplate"
    model = RefQuotaDefinitionRange

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
