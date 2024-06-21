from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import CreateView
from django.views.generic import DeleteView
from django.views.generic import UpdateView

from reference_documents.forms.ref_order_number_forms import (
    RefOrderNumberCreateUpdateForm, RefOrderNumberDeleteForm,
)
from reference_documents.models import ReferenceDocumentVersion, RefOrderNumber


class RefOrderNumberEdit(PermissionRequiredMixin, UpdateView):
    template_name = "reference_documents/ref_order_numbers/edit.jinja"
    permission_required = "change_refordernumber"
    model = RefOrderNumber
    form_class = RefOrderNumberCreateUpdateForm

    def get_form_kwargs(self):
        kwargs = super(RefOrderNumberEdit, self).get_form_kwargs()
        kwargs["reference_document_version"] = RefOrderNumber.objects.get(
            id=self.kwargs["pk"],
        ).reference_document_version
        return kwargs

    def get_success_url(self):
        return (
            reverse(
                "reference_documents:version-details",
                args=[self.get_object().reference_document_version.pk],
            )
            + "#tariff-quotas"
        )


class RefOrderNumberCreate(PermissionRequiredMixin, CreateView):
    template_name = "reference_documents/ref_order_numbers/edit.jinja"
    permission_required = "reference_documents.add_refordernumber"
    model = RefOrderNumber
    form_class = RefOrderNumberCreateUpdateForm

    def get_form_kwargs(self):
        kwargs = super(RefOrderNumberCreate, self).get_form_kwargs()
        kwargs["reference_document_version"] = ReferenceDocumentVersion.objects.get(
            id=self.kwargs["pk"],
        )

        return kwargs

    def form_valid(self, form):
        instance = form.instance
        reference_document_version = ReferenceDocumentVersion.objects.get(
            pk=self.kwargs["pk"],
        )
        instance.reference_document_version = reference_document_version
        self.object = instance
        return super(RefOrderNumberCreate, self).form_valid(form)

    def get_success_url(self):
        return (
            reverse(
                "reference_documents:version-details",
                args=[self.object.reference_document_version.pk],
            )
            + "#tariff-quotas"
        )

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["reference_document_version"] = (
            ReferenceDocumentVersion.objects.all().get(pk=self.kwargs.get("pk"))
        )
        return context_data


class RefOrderNumberDelete(
    PermissionRequiredMixin,
    DeleteView,
):
    form_class = RefOrderNumberDeleteForm
    template_name = "reference_documents/ref_order_numbers/delete.jinja"
    permission_required = "delete_refordernumber"
    model = RefOrderNumber

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
                "order_number": f"{self.object.order_number}",
            }
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        self.object.delete()
        return redirect(self.get_success_url())
