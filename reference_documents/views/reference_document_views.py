from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import CreateView
from django.views.generic import DeleteView
from django.views.generic import DetailView
from django.views.generic import ListView
from django.views.generic import TemplateView
from django.views.generic import UpdateView

from reference_documents import models
from reference_documents.forms.reference_document_forms import (
    ReferenceDocumentCreateUpdateForm,
)
from reference_documents.forms.reference_document_forms import (
    ReferenceDocumentDeleteForm,
)
from reference_documents.models import ReferenceDocument, ReferenceDocumentVersionStatus


class ReferenceDocumentContext:
    def __init__(self, object_list, user):
        self.object_list = object_list
        self.user = user

    def get_reference_document_context_headers(self):
        return [
            {"text": "Latest Version"},
            {"text": "Country"},
            {"text": "Rates"},
            {"text": "Order Numbers"},
            {"text": "Regulations"},
            {"text": "Actions"},
        ]

    def get_reference_document_context_rows(self):
        reference_documents = []
        for ref_doc in self.object_list.order_by("area_id"):
            if ref_doc.reference_document_versions.count() == 0:

                actions = ''

                if self.user.has_perm("reference_documents.view_referencedocument"):
                    actions += f'<a href="/reference_documents/{ref_doc.id}">Details</a><br>'

                if self.user.has_perm("reference_documents.change_referencedocument"):
                    actions += f"<a href={reverse('reference_documents:edit', kwargs={'pk': ref_doc.id})}>Edit</a><br>"

                if self.user.has_perm("reference_documents.delete_referencedocument"):
                    actions += f"<a href={reverse('reference_documents:delete', kwargs={'pk': ref_doc.id})}>Delete</a>"

                reference_documents.append(
                    [
                        {"text": "-"},
                        {
                            "text": f"{ref_doc.area_id} - ({ref_doc.get_area_name_by_area_id()})",
                        },
                        {"text": '-'},
                        {"text": '-'},
                        {"text": ref_doc.regulations},
                        {
                            "html": actions
                        },
                    ],
                )

            else:
                actions = ""

                if self.user.has_perm("reference_documents.view_referencedocument"):
                    actions += f'<a href="/reference_documents/{ref_doc.id}">Details</a><br>'

                if ref_doc.editable():
                    if self.user.has_perm("reference_documents.change_referencedocument"):
                        actions += f"<a href={reverse('reference_documents:edit', kwargs={'pk': ref_doc.id})}>Edit</a><br>"

                    if self.user.has_perm("reference_documents.delete_referencedocument"):
                        actions += f"<a href={reverse('reference_documents:delete', kwargs={'pk': ref_doc.id})}>Delete</a>"

                reference_documents.append(
                    [
                        {"text": ref_doc.reference_document_versions.last().version},
                        {
                            "text": f"{ref_doc.area_id} - ({ref_doc.get_area_name_by_area_id()})",
                        },
                        {
                            "text": ref_doc.reference_document_versions.last().ref_rates.count(),
                        },
                        {
                            "text": ref_doc.reference_document_versions.last().ref_order_numbers.count(),
                        },
                        {
                            "text": ref_doc.regulations,
                        },
                        {
                            "html": actions
                        },
                    ],
                )
        return reference_documents

    def get_context(self):
        return {
            "reference_documents": self.get_reference_document_context_rows(),
            "reference_document_headers": self.get_reference_document_context_headers(),
        }


class ReferenceDocumentList(PermissionRequiredMixin, ListView):
    template_name = "reference_documents/index.jinja"
    permission_required = "reference_documents.view_referencedocument"
    model = ReferenceDocument

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(ReferenceDocumentContext(context["object_list"], self.request.user).get_context())
        return context


class ReferenceDocumentDetails(PermissionRequiredMixin, DetailView):
    template_name = "reference_documents/details.jinja"
    permission_required = "reference_documents.view_referencedocument"
    model = ReferenceDocument

    def get_context_data(self, *args, **kwargs):
        context = super(ReferenceDocumentDetails, self).get_context_data(
            *args,
            **kwargs,
        )

        context["reference_document_versions_headers"] = [
            {"text": "Version"},
            {"text": "Status"},
            {"text": "Duties"},
            {"text": "Order Numbers"},
            {"text": "EIF date"},
            {"text": "Actions"},
        ]
        reference_document_versions = []

        for version in context["object"].reference_document_versions.order_by(
                "version",
        ):
            actions = ""

            if self.request.user.has_perm("reference_documents.view_referencedocumentversion"):
                actions += f'<a href="{reverse("reference_documents:version-details", kwargs={"pk": version.id})}">Version details</a><br>'

            if version.status == ReferenceDocumentVersionStatus.EDITING:
                if self.request.user.has_perm("reference_documents.change_referencedocumentversion"):
                    actions += f'<a href="{reverse("reference_documents:version-edit", kwargs={"ref_doc_pk": context["object"].pk, "pk": version.id})}">Edit</a><br>'
                if self.request.user.has_perm("reference_documents.delete_referencedocumentversion"):
                    actions += f'<a href="{reverse("reference_documents:version-delete", kwargs={"ref_doc_pk": context["object"].pk, "pk": version.id})}">Delete</a><br>'
                if self.request.user.has_perm("reference_documents.change_referencedocumentversion"):
                    actions += f'<a href="{reverse("reference_documents:version-status-change-to-in-review", kwargs={"ref_doc_pk": context["object"].pk, "pk": version.id})}">Ready for review</a><br>'
            elif version.status == ReferenceDocumentVersionStatus.IN_REVIEW:
                if self.request.user.has_perm("reference_documents.change_referencedocumentversion"):
                    actions += f'<a href="{reverse("reference_documents:version-status-change-to-published", kwargs={"ref_doc_pk": context["object"].pk, "pk": version.id})}">Ready to publish</a><br>'
                if self.request.user.has_perm("reference_documents.change_referencedocumentversion"):
                    actions += f'<a href="{reverse("reference_documents:version-status-change-to-editing", kwargs={"ref_doc_pk": context["object"].pk, "pk": version.id})}">Revert to editable</a><br>'
            else:
                if self.request.user.is_superuser:
                    actions += f'<a href="{reverse("reference_documents:version-status-change-to-editing", kwargs={"ref_doc_pk": context["object"].pk, "pk": version.id})}">Revert to editable</a><br>'

            reference_document_versions.append(
                [
                    {
                        "text": version.version,
                    },
                    {
                        "text": version.status,
                    },
                    {
                        "text": version.ref_rates.count(),
                    },
                    {
                        "text": version.ref_order_numbers.count(),
                    },
                    {
                        "text": version.entry_into_force_date,
                    },
                    {
                        "html": actions
                    },
                ],
            )

        context["reference_document_versions"] = reference_document_versions

        return context


class ReferenceDocumentCreate(PermissionRequiredMixin, CreateView):
    template_name = "reference_documents/create.jinja"
    permission_required = "reference_documents.add_referencedocument"
    form_class = ReferenceDocumentCreateUpdateForm

    def get_success_url(self):
        return reverse(
            "reference_documents:confirm-create",
            kwargs={"pk": self.object.pk},
        )


class ReferenceDocumentEdit(PermissionRequiredMixin, UpdateView):
    model = models.ReferenceDocument
    permission_required = "reference_documents.change_referencedocument"
    template_name = "reference_documents/update.jinja"
    form_class = ReferenceDocumentCreateUpdateForm

    def get_success_url(self):
        return reverse(
            "reference_documents:confirm-update",
            kwargs={"pk": self.object.pk},
        )


class ReferenceDocumentDelete(PermissionRequiredMixin, DeleteView):
    form_class = ReferenceDocumentDeleteForm
    model = ReferenceDocument
    permission_required = "reference_documents.delete_referencedocument"
    template_name = "reference_documents/delete.jinja"

    def get_success_url(self) -> str:
        return reverse(
            "reference_documents:confirm-delete",
            kwargs={"deleted_pk": self.kwargs["pk"]},
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
                "area_id": f"{self.object.area_id}",
            }
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        self.object.delete()
        return redirect(self.get_success_url())


class ReferenceDocumentConfirmCreate(DetailView):
    template_name = "reference_documents/confirm_create.jinja"
    model = ReferenceDocument


class ReferenceDocumentConfirmUpdate(DetailView):
    template_name = "reference_documents/confirm_update.jinja"
    model = ReferenceDocument


class ReferenceDocumentConfirmDelete(TemplateView):
    template_name = "reference_documents/confirm_delete.jinja"

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["deleted_pk"] = self.kwargs["deleted_pk"]
        return context_data
