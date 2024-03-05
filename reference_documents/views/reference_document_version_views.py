from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import CreateView
from django.views.generic import DeleteView
from django.views.generic import DetailView
from django.views.generic import TemplateView
from django.views.generic import UpdateView
from django.views.generic.edit import FormMixin

from commodities.models import GoodsNomenclature
from geo_areas.models import GeographicalAreaDescription
from quotas.models import QuotaOrderNumber
from reference_documents import forms
from reference_documents.models import AlignmentReportCheckStatus
from reference_documents.models import ReferenceDocument
from reference_documents.models import ReferenceDocumentVersion


class ReferenceDocumentVersionDetails(PermissionRequiredMixin, DetailView):
    template_name = "reference_documents/reference_document_versions/details.jinja"
    permission_required = "reference_documents.view_reference_documentversion"
    model = ReferenceDocumentVersion

    def get_country_by_area_id(self, area_id):
        description = (
            GeographicalAreaDescription.objects.latest_approved()
            .filter(described_geographicalarea__area_id=area_id)
            .order_by("-validity_start")
            .first()
        )
        if description:
            return description.description
        else:
            return f"{area_id} (unknown description)"

    def get_tap_comm_code(self, duty):
        if duty.reference_document_version.entry_into_force_date is not None:
            contains_date = duty.reference_document_version.entry_into_force_date
        else:
            contains_date = duty.reference_document_version.published_date

        goods = GoodsNomenclature.objects.latest_approved().filter(
            item_id=duty.commodity_code,
            valid_between__contains=contains_date,
            suffix=80,
        )

        if len(goods) == 0:
            return None

        return goods.first()

    def get_tap_order_number(self, quota):
        # todo: This needs to consider the validity period(s)
        # may need to handle in the pre processing of the data e.g. where the volume defines multiple periods

        if quota.reference_document_version.entry_into_force_date is not None:
            contains_date = quota.reference_document_version.entry_into_force_date
        else:
            contains_date = quota.reference_document_version.published_date

        quota_order_number = QuotaOrderNumber.objects.latest_approved().filter(
            order_number=quota.quota_order_number,
            valid_between__contains=contains_date,
        )

        if len(quota_order_number) == 0:
            return None

        return quota_order_number.first()

    def get_context_data(self, *args, **kwargs):
        context = super(ReferenceDocumentVersionDetails, self).get_context_data(
            *args,
            **kwargs,
        )
        ref_doc = context["object"].reference_document

        # title
        context[
            "ref_doc_title"
        ] = f"Reference Document for {ref_doc.get_area_name_by_area_id()}"

        context["reference_document_version_duties_headers"] = [
            {"text": "Comm Code"},
            {"text": "Duty Rate"},
            {"text": "Validity"},
            {"text": "Checks"},
            {"text": "Actions"},
        ]

        context["reference_document_version_quotas_headers"] = [
            {"text": "Comm Code"},
            {"text": "Rate"},
            {"text": "Volume"},
            {"text": "Validity"},
            {"text": "Checks"},
            {"text": "Actions"},
        ]

        reference_document_version_duties = []
        reference_document_version_quotas = {}

        latest_alignment_report = context["object"].alignment_reports.last()

        for duty in context["object"].preferential_rates.order_by("commodity_code"):
            failure_count = (
                duty.preferential_rate_checks.all()
                .filter(
                    alignment_report=latest_alignment_report,
                    status=AlignmentReportCheckStatus.FAIL,
                )
                .count()
            )

            check_count = (
                duty.preferential_rate_checks.all()
                .filter(
                    alignment_report=latest_alignment_report,
                )
                .count()
            )

            if failure_count > 0:
                checks_output = f'<div class="check-failing">FAIL</div>'
            elif check_count == 0:
                checks_output = f"N/A"
            else:
                checks_output = f'<div class="check-passing">PASS</div>'

            comm_code = self.get_tap_comm_code(duty)

            if comm_code:
                comm_code_link = f'<a class="govuk-link" href="{comm_code.get_url()}">{comm_code.item_id}</a>'
            else:
                comm_code_link = f"{duty.commodity_code}"

            reference_document_version_duties.append(
                [
                    {
                        "html": comm_code_link,
                    },
                    {
                        "text": duty.duty_rate,
                    },
                    {
                        "text": duty.valid_between,
                    },
                    {
                        "html": checks_output,
                    },
                    {
                        "html": f"<a href='{reverse('reference_documents:preferential_rates_edit', args=[duty.pk])}'>Edit</a> "
                        f"<a href='{reverse('reference_documents:preferential_rates_delete', args=[duty.pk])}'>Delete</a>",
                    },
                ],
            )

        # order numbers
        for quota in context["object"].preferential_quotas.order_by("order"):
            failure_count = (
                quota.preferential_quota_checks.all()
                .filter(
                    alignment_report=latest_alignment_report,
                    status=AlignmentReportCheckStatus.FAIL,
                )
                .count()
            )

            check_count = (
                quota.preferential_quota_checks.all()
                .filter(
                    alignment_report=latest_alignment_report,
                )
                .count()
            )

            if failure_count > 0:
                checks_output = f'<div class="check-failing">FAIL</div>'
            elif check_count == 0:
                checks_output = f"N/A"
            else:
                checks_output = f'<div class="check-passing">PASS</div>'

            quota_order_number = self.get_tap_order_number(quota)

            comm_code = self.get_tap_comm_code(quota)
            if comm_code:
                comm_code_link = f'<a class="govuk-link" href="{comm_code.get_url()}">{comm_code.structure_code}</a>'
            else:
                comm_code_link = f"{quota.commodity_code}"

            row_to_add = [
                {
                    "html": comm_code_link,
                },
                {
                    "text": quota.quota_duty_rate,
                },
                {
                    "text": f"{quota.volume} {quota.measurement}",
                },
                {
                    "text": quota.valid_between,
                },
                {
                    "html": checks_output,
                },
                {
                    "html": f"<a href='{reverse('reference_documents:preferential_quotas_edit', args=[quota.pk])}'>Edit</a> "
                    f"<a href='{reverse('reference_documents:preferential_quotas_delete', args=[quota.pk])}'>Delete</a>",
                },
            ]

            if quota.quota_order_number in reference_document_version_quotas.keys():
                reference_document_version_quotas[quota.quota_order_number][
                    "data_rows"
                ].append(
                    row_to_add,
                )
            else:
                reference_document_version_quotas[quota.quota_order_number] = {
                    "data_rows": [row_to_add],
                    "quota_order_number": quota_order_number,
                }

        context["reference_document_version_duties"] = reference_document_version_duties
        context["reference_document_version_quotas"] = reference_document_version_quotas

        return context


class ReferenceDocumentVersionCreate(PermissionRequiredMixin, CreateView):
    template_name = "reference_documents/reference_document_versions/create.jinja"
    permission_required = "reference_documents.add_referencedocumentversion"
    form_class = forms.ReferenceDocumentVersionsEditCreateForm

    def get_initial(self):
        initial = super().get_initial()
        initial["reference_document"] = ReferenceDocument.objects.all().get(
            pk=self.kwargs["pk"],
        )
        return initial

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        print(self.kwargs)
        context_data["reference_document"] = ReferenceDocument.objects.all().get(
            pk=self.kwargs["pk"],
        )
        return context_data

    def get_success_url(self):
        return reverse(
            "reference_documents:version-confirm-create",
            kwargs={"pk": self.object.pk},
        )


class ReferenceDocumentVersionEdit(PermissionRequiredMixin, UpdateView):
    model = ReferenceDocumentVersion
    permission_required = "reference_documents.change_referencedocumentversion"
    template_name = "reference_documents/reference_document_versions/edit.jinja"
    form_class = forms.ReferenceDocumentVersionsEditCreateForm

    def get_success_url(self):
        return reverse(
            "reference_documents:version-confirm-update",
            kwargs={"pk": self.object.pk},
        )


class ReferenceDocumentVersionDelete(PermissionRequiredMixin, FormMixin, DeleteView):
    form_class = forms.ReferenceDocumentVersionDeleteForm
    model = ReferenceDocumentVersion
    permission_required = "reference_documents.delete_referencedocumentversion"
    template_name = "reference_documents/reference_document_versions/delete.jinja"

    # TODO: Update this to get rid of FormMixin with Django 4.2 as no need to overwrite the post anymore
    def get_success_url(self) -> str:
        return reverse(
            "reference_documents:version-confirm-delete",
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
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        self.object.delete()
        return redirect(self.get_success_url())


class ReferenceDocumentVersionConfirmCreate(DetailView):
    template_name = (
        "reference_documents/reference_document_versions/confirm_create.jinja"
    )
    model = ReferenceDocument


class ReferenceDocumentVersionConfirmUpdate(DetailView):
    template_name = (
        "reference_documents/reference_document_versions/confirm_update.jinja"
    )
    model = ReferenceDocument


class ReferenceDocumentVersionConfirmDelete(TemplateView):
    template_name = (
        "reference_documents/reference_document_versions/confirm_delete.jinja"
    )

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["deleted_pk"] = self.kwargs["deleted_pk"]
        return context_data
