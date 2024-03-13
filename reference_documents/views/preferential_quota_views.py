from datetime import date

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import CreateView
from django.views.generic import FormView
from django.views.generic import UpdateView

from common.util import TaricDateRange
from reference_documents.forms.preferential_quota_forms import (
    PreferentialQuotaBulkCreate,
)
from reference_documents.forms.preferential_quota_forms import (
    PreferentialQuotaCreateUpdateForm,
)
from reference_documents.models import PreferentialQuota
from reference_documents.models import PreferentialQuotaOrderNumber
from reference_documents.models import ReferenceDocumentVersion


class PreferentialQuotaEditView(PermissionRequiredMixin, UpdateView):
    template_name = "reference_documents/preferential_quotas/edit.jinja"
    permission_required = "reference_documents.edit_reference_document"
    model = PreferentialQuota
    form_class = PreferentialQuotaCreateUpdateForm

    def get_form_kwargs(self):
        kwargs = super(PreferentialQuotaEditView, self).get_form_kwargs()
        kwargs["reference_document_version"] = PreferentialQuotaOrderNumber.objects.get(
            id=self.kwargs["pk"],
        ).reference_document_version
        return kwargs

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

    def get_form_kwargs(self):
        kwargs = super(PreferentialQuotaCreateView, self).get_form_kwargs()
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
        return super(PreferentialQuotaCreateView, self).form_valid(form)

    def get_success_url(self):
        return (
            reverse(
                "reference_documents:version-details",
                args=[self.object.reference_document_version.pk],
            )
            + "#tariff-quotas"
        )


class PreferentialQuotaBulkCreateView(PermissionRequiredMixin, FormView):
    template_name = "reference_documents/preferential_quotas/bulk_create.jinja"
    permission_required = "reference_documents.add_preferentialquota"
    # model = PreferentialQuota
    form_class = PreferentialQuotaBulkCreate
    queryset = ReferenceDocumentVersion.objects.all()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs[
            "reference_document_version"
        ] = ReferenceDocumentVersion.objects.all().get(
            pk=self.kwargs["pk"],
        )
        return kwargs

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data[
            "reference_document_version"
        ] = ReferenceDocumentVersion.objects.all().get(
            pk=self.kwargs["pk"],
        )
        return context_data

    @staticmethod
    def get_validity_and_volume_data(data):
        entries = []
        for entry in range(len(data.getlist("volume"))):
            start_date = date(
                day=int(data.getlist("start_date_0")[entry]),
                month=int(data.getlist("start_date_1")[entry]),
                year=int(data.getlist("start_date_2")[entry]),
            )
            end_date = date(
                day=int(data.getlist("end_date_0")[entry]),
                month=int(data.getlist("end_date_1")[entry]),
                year=int(data.getlist("end_date_2")[entry]),
            )
            valid_between = TaricDateRange(start_date, end_date)
            volume = data.getlist("volume")[entry]
            entries.append({f"valid_between": valid_between, f"volume": volume})
        return entries

    def form_valid(self, form):
        dates_and_volumes = self.get_validity_and_volume_data(form.data)
        commodity_codes = form.cleaned_data["commodity_codes"].splitlines()
        self.reference_document_version = ReferenceDocumentVersion.objects.all().get(
            pk=self.kwargs["pk"],
        )
        for commodity_code in commodity_codes:
            for entry in dates_and_volumes:
                instance = form.save(commit=False)
                instance.order = (
                    len(self.reference_document_version.preferential_quotas()) + 1
                )
                instance = PreferentialQuota(
                    commodity_code=commodity_code,
                    quota_duty_rate=instance.quota_duty_rate,
                    volume=entry["volume"],
                    valid_between=entry["valid_between"],
                    measurement=instance.measurement,
                    order=instance.order,
                    preferential_quota_order_number=instance.preferential_quota_order_number,
                )
                instance.save()
        return redirect(self.get_success_url())

    def get_success_url(self):
        return (
            reverse(
                "reference_documents:version-details",
                args=[self.reference_document_version.pk],
            )
            + "#tariff-quotas"
        )


class PreferentialQuotaDeleteView(PermissionRequiredMixin, UpdateView):
    template_name = "preferential_quotas/delete.jinja"
    permission_required = "reference_documents.edit_reference_document"
    model = PreferentialQuota
