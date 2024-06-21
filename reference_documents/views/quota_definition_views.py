from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import CreateView
from django.views.generic import FormView
from django.views.generic import UpdateView
from django.views.generic.edit import DeleteView

from reference_documents.forms.ref_quota_definition_forms import (
    RefQuotaDefinitionBulkCreateForm,
    RefQuotaDefinitionCreateUpdateForm,
    RefQuotaDefinitionDeleteForm
)

from reference_documents.models import RefQuotaDefinition
from reference_documents.models import ReferenceDocumentVersion


class RefQuotaDefinitionEdit(PermissionRequiredMixin, UpdateView):
    template_name = "reference_documents/ref_quota_definitions/edit.jinja"
    permission_required = "reference_documents.change_preferentialquota"
    model = RefQuotaDefinition
    form_class = RefQuotaDefinitionCreateUpdateForm

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
        kwargs = super(RefQuotaDefinitionEdit, self).get_form_kwargs()
        kwargs["reference_document_version"] = RefQuotaDefinition.objects.get(
            id=self.kwargs["pk"],
        ).ref_order_number.reference_document_version
        kwargs["ref_order_number"] = RefQuotaDefinition.objects.get(
            id=self.kwargs["pk"],
        ).ref_order_number
        return kwargs


class RefQuotaDefinitionCreate(PermissionRequiredMixin, CreateView):
    template_name = "reference_documents/ref_quota_definitions/create.jinja"
    permission_required = "reference_documents.add_refquotadefinition"
    model = RefQuotaDefinition
    form_class = RefQuotaDefinitionCreateUpdateForm

    def get_form_kwargs(self):
        kwargs = super(RefQuotaDefinitionCreate, self).get_form_kwargs()
        kwargs["reference_document_version"] = ReferenceDocumentVersion.objects.get(
            id=self.kwargs["version_pk"],
        )

        if "order_pk" in self.kwargs.keys():
            kwargs["ref_order_number"] = kwargs["reference_document_version"].ref_order_numbers.get(
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
        return super(RefQuotaDefinitionCreate, self).form_valid(form)

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


class RefQuotaDefinitionBulkCreate(PermissionRequiredMixin, FormView):
    template_name = "reference_documents/ref_quota_definitions/bulk_create.jinja"
    permission_required = "reference_documents.add_refquotadefinition"
    form_class = RefQuotaDefinitionBulkCreateForm
    queryset = ReferenceDocumentVersion.objects.all()

    def get_reference_document_version(self):
        return ReferenceDocumentVersion.objects.all().get(
            pk=self.kwargs["pk"],
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["reference_document_version"] = self.get_reference_document_version()
        if "order_pk" in self.kwargs.keys():
            kwargs["ref_order_number"] = kwargs[
                "reference_document_version"
            ].ref_order_numbers.get(
                id=self.kwargs["order_pk"],
            )
        else:
            kwargs["ref_order_number"] = None
        return kwargs

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["reference_document_version"] = (
            self.get_reference_document_version()
        )
        return context_data

    def form_valid(self, form):
        cleaned_data = form.cleaned_data
        commodity_codes = set(form.cleaned_data["commodity_codes"].splitlines())
        for commodity_code in commodity_codes:
            for index in form.variant_indices:
                RefQuotaDefinition.objects.create(
                    commodity_code=commodity_code,
                    duty_rate=cleaned_data["duty_rate"],
                    volume=cleaned_data[f"volume_{index}"],
                    valid_between=cleaned_data[f"valid_between_{index}"],
                    measurement=cleaned_data["measurement"],
                    ref_order_number=cleaned_data[
                        "ref_order_number"
                    ],
                )
        return redirect(self.get_success_url())

    def get_success_url(self):
        return (
                reverse(
                    "reference_documents:version-details",
                    args=[self.get_reference_document_version().pk],
                )
                + "#tariff-quotas"
        )


class RefQuotaDefinitionDelete(PermissionRequiredMixin, DeleteView):
    form_class = RefQuotaDefinitionDeleteForm
    template_name = "reference_documents/ref_quota_definitions/delete.jinja"
    permission_required = "reference_documents.delete_refquotadefinition"
    model = RefQuotaDefinition

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
