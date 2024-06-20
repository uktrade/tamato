from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import CreateView
from django.views.generic import DeleteView
from django.views.generic import DetailView
from django.views.generic import ListView
from django.views.generic import TemplateView
from django.views.generic import UpdateView

from commodities.models import GoodsNomenclature
from quotas.models import QuotaOrderNumber
from reference_documents.forms.reference_document_version_forms import (
    ReferenceDocumentVersionDeleteForm,
)
from reference_documents.forms.reference_document_version_forms import (
    ReferenceDocumentVersionsCreateUpdateForm,
)
from reference_documents.models import AlignmentReportCheck, AlignmentReport, RefQuotaSuspension, RefQuotaSuspensionRange, RefQuotaDefinition, RefQuotaDefinitionRange, AlignmentReportStatus
from reference_documents.models import RefOrderNumber
from reference_documents.models import ReferenceDocument
from reference_documents.models import ReferenceDocumentVersion
from reference_documents.models import ReferenceDocumentVersionStatus
from reference_documents.tasks import run_alignment_check


class QuotaDefinitionContext:
    def __init__(self, quota_definition: RefQuotaDefinition, user):
        self.user = user
        self.quota_definition = quota_definition
        self.reference_document_version = quota_definition.ref_order_number.reference_document_version

    def row(self):
        # comm_code = ReferenceDocumentVersionContext.get_tap_comm_code(
        #     self.reference_document_version,
        #     self.quota_definition.commodity_code,
        # )
        # if comm_code:
        #     comm_code_link = f'<a class="govuk-link" href="{comm_code.get_url()}">{comm_code.structure_code}</a>'
        # else:
        comm_code_link = f"{self.quota_definition.commodity_code}"

        actions = "<span></span>"

        if self.reference_document_version.editable():
            if self.quota_definition and self.quota_definition.pk:
                if self.user.has_perm("reference_documents.change_preferentialquotaordernumber"):
                    actions += f"<a href='{reverse('reference_documents:quota-definition-edit', args=[self.quota_definition.pk])}'>Edit</a>"
                if self.user.has_perm("reference_documents.delete_preferentialquotaordernumber"):
                    actions += f" | <a href='{reverse('reference_documents:quota-definition-delete', args=[self.quota_definition.pk, self.quota_definition.ref_order_number.reference_document_version.pk])}'>Delete</a>"

        row_data = [
            {
                "html": comm_code_link,
            },
            {
                "text": self.quota_definition.duty_rate,
            },
            {
                "text": f"{self.quota_definition.volume} {self.quota_definition.measurement}",
            },
            {
                "text": self.quota_definition.valid_between,
            },
            {
                "html": actions,
            },
        ]

        return row_data


class QuotaDefinitionTemplateContext:
    def __init__(self, quota_definition_range: RefQuotaDefinitionRange, user):
        self.user = user
        self.quota_definition_range = quota_definition_range
        self.reference_document_version = quota_definition_range.ref_order_number.reference_document_version
        self.quota_defs = []

    def quota_def_template_data_rows(self):
        for quota_def in self.quota_defs:
            yield quota_def.row()


class QuotaSuspensionTemplateContext:
    def __init__(self, quota_suspension_range: RefQuotaSuspensionRange, user):
        self.user = user
        self.quota_suspension_template = quota_suspension_range
        self.reference_document_version = quota_suspension_range.ref_quota_definition_range.ref_order_number.reference_document_version
        self.quota_suspensions = []

    def quota_suspensions_template_data_rows(self):
        for quota_suspension in self.quota_suspensions:
            yield quota_suspension.row()


class QuotaSuspensionContext:

    def __init__(self, quota_suspension: RefQuotaSuspension, user):
        self.user = user
        self.quota_suspension = quota_suspension
        self.reference_document_version = quota_suspension.ref_quota_definition.ref_order_number.reference_document_version

    def row(self):
        # comm_code = ReferenceDocumentVersionContext.get_tap_comm_code(
        #     self.reference_document_version,
        #     self.quota_suspension.preferential_quota.commodity_code,
        # )

        # if comm_code:
        #     comm_code_link = f'<a class="govuk-link" href="{comm_code.get_url()}">{comm_code.structure_code}</a>'
        # else:
        comm_code_link = f"{self.quota_suspension.ref_quota_definition.commodity_code}"

        actions = "<span></span>"

        if self.reference_document_version.editable():
            if self.quota_suspension.pk:
                if self.user.has_perm("reference_documents.change_preferentialquotasuspension"):
                    actions += f"<a href='{reverse('reference_documents:quota-suspension-edit', args=[self.quota_suspension.pk])}'>Edit</a>"
                if self.user.has_perm("reference_documents.delete_preferentialquotasuspension"):
                    actions += f" | <a href='{reverse('reference_documents:quota-suspension-delete', args=[self.quota_suspension.pk, self.reference_document_version.pk])}'>Delete</a>"

        row_data = [
            {
                "html": comm_code_link,
            },
            {
                "text": self.quota_suspension.valid_between,
            },
            {
                "text": self.quota_suspension.ref_quota_definition.valid_between,
            },
            {
                "html": actions,
            },
        ]

        return row_data


class OrderNumberContext:
    def __init__(self, order_number: RefOrderNumber, version: ReferenceDocumentVersion, tap_order_number):
        self.order_number = order_number
        self.tap_order_number = tap_order_number
        self.version = version
        self.quota_defs = []
        self.quota_suspension_defs = []
        self.quota_def_templates = []
        self.quota_suspension_templates = []

    def quota_def_data_rows(self):
        for quota_def in self.quota_defs:
            yield quota_def.row()

    def quota_suspensions_data_rows(self):
        for quota_suspension in self.quota_suspension_defs:
            yield quota_suspension.row()


class ReferenceDocumentVersionContext:
    def __init__(self, reference_document_version: ReferenceDocumentVersion, user):
        self.reference_document_version = reference_document_version
        self.user = user
        self.order_numbers = []
        self._populate_order_numbers()
        self._populate_quota_definitions()
        self._populate_quota_suspensions()
        self._populate_quota_definition_ranges()
        self._populate_quota_suspension_templates()

    def _populate_order_numbers(self):

        for ref_doc_order_number in self.reference_document_version.ref_order_numbers.order_by(
                "order_number",
        ):
            tap_order_number = self.get_tap_order_number(ref_doc_order_number)

            self.order_numbers.append(
                OrderNumberContext(
                    ref_doc_order_number,
                    self.reference_document_version,
                    tap_order_number=tap_order_number
                )
            )

    def _populate_quota_definitions(self):
        for context_order_number in self.order_numbers:
            for quota in context_order_number.order_number.ref_quota_definitions.order_by(
                    "commodity_code"
            ):
                context_order_number.quota_defs.append(QuotaDefinitionContext(quota, self.user))

    def _populate_quota_suspensions(self):
        for context_order_number in self.order_numbers:
            for context_quota_def in context_order_number.quota_defs:
                for suspension in context_quota_def.quota_definition.ref_quota_suspensions.all():
                    context_order_number.quota_suspension_defs.append(QuotaSuspensionContext(suspension, self.user))

    def _populate_quota_definition_ranges(self):
        for context_order_number in self.order_numbers:
            for quota_definition_range in context_order_number.order_number.ref_quota_definition_ranges.all():
                new_context = QuotaDefinitionTemplateContext(quota_definition_range, self.user)
                context_order_number.quota_def_templates.append(new_context)
                for quota_definition in quota_definition_range.dynamic_quota_definitions():
                    new_context.quota_defs.append(QuotaDefinitionContext(quota_definition, self.user))

    def _populate_quota_suspension_templates(self):
        for context_order_number in self.order_numbers:
            for quota_definition_range in context_order_number.order_number.ref_quota_definition_ranges.all():
                for quota_suspension_range in quota_definition_range.ref_quota_suspension_ranges.all():
                    new_context = QuotaSuspensionTemplateContext(quota_suspension_range, self.user)
                    context_order_number.quota_suspension_templates.append(new_context)
                    for quota_suspension in quota_suspension_range.dynamic_quota_suspensions():
                        new_context.quota_suspensions.append(QuotaSuspensionContext(quota_suspension, self.user))

    def alignment_report(self):
        return self.reference_document_version.alignment_reports.last()

    @staticmethod
    def get_tap_order_number(
            ref_doc_quota_order_number: RefOrderNumber,
    ):
        if (
                ref_doc_quota_order_number.reference_document_version.entry_into_force_date
                is not None
        ):
            contains_date = (
                ref_doc_quota_order_number.reference_document_version.entry_into_force_date
            )
        else:
            contains_date = (
                ref_doc_quota_order_number.reference_document_version.published_date
            )

        quota_order_number = QuotaOrderNumber.objects.latest_approved().filter(
            order_number=ref_doc_quota_order_number.order_number,
            valid_between__contains=contains_date,
        )

        if len(quota_order_number) == 0:
            return None

        return quota_order_number.first()

    @staticmethod
    def get_tap_comm_code(
            ref_doc_version: ReferenceDocumentVersion,
            comm_code: str,
    ):
        if ref_doc_version.entry_into_force_date is not None:
            contains_date = ref_doc_version.entry_into_force_date
        else:
            contains_date = ref_doc_version.published_date

        goods = GoodsNomenclature.objects.latest_approved().filter(
            item_id=comm_code,
            valid_between__contains=contains_date,
            suffix=80,
        )

        if len(goods) == 0:
            return None

        return goods.first()

    def duties_headers(self):
        return [
            {"text": "Comm Code"},
            {"text": "Duty Rate"},
            {"text": "Validity"},
            {"text": "Actions"},
        ]

    def quotas_headers(self):
        return [
            {"text": "Comm Code"},
            {"text": "Rate"},
            {"text": "Volume"},
            {"text": "Validity"},
            {"text": "Actions"},
        ]

    def suspension_headers(self):
        return [
            {"text": "Comm Code"},
            {"text": "Validity"},
            {"text": "Quota Validity"},
            {"text": "Actions"},
        ]

    def templated_quotas_headers(self):
        return [
            {"text": "Comm Code"},
            {"text": "Rate"},
            {"text": "Volume"},
            {"text": "Validity"},
        ]

    def duties_row_data(self):
        rows = []
        for (
                preferential_rate
        ) in self.reference_document_version.ref_rates.order_by(
            "commodity_code", "valid_between"
        ):
            # comm_code = ReferenceDocumentVersionContext.get_tap_comm_code(
            #     preferential_rate.reference_document_version,
            #     preferential_rate.commodity_code,
            # )

            # if comm_code:
            #     comm_code_link = f'<a class="govuk-link" href="{comm_code.get_url()}">{comm_code.item_id}</a>'
            # else:
            comm_code_link = f"{preferential_rate.commodity_code}"

            actions = "<span></span>"

            if self.reference_document_version.editable():
                if self.user.has_perm("reference_documents.change_preferentialrate"):
                    actions += f"<a href='{reverse('reference_documents:rate-edit', args=[preferential_rate.pk])}'>Edit</a>"
                if self.user.has_perm("reference_documents.delete_preferentialrate"):
                    actions += f" | <a href='{reverse('reference_documents:rate-delete', args=[preferential_rate.pk])}'>Delete</a>"

            rows.append(
                [
                    {
                        "html": comm_code_link,
                    },
                    {
                        "text": preferential_rate.duty_rate,
                    },
                    {
                        "text": preferential_rate.valid_between,
                    },
                    {
                        "html": actions,
                    },
                ],
            )
        return rows

    def get_quota_row(self, commodity_code: str, volume, measurement, duty_rate, valid_between, quota=None):

        # comm_code = ReferenceDocumentVersionContext.get_tap_comm_code(
        #     self.reference_document_version,
        #     commodity_code,
        # )
        # if comm_code:
        #     comm_code_link = f'<a class="govuk-link" href="{comm_code.get_url()}">{comm_code.structure_code}</a>'
        # else:
        comm_code_link = f"{commodity_code}"

        actions = "<span></span>"

        if self.reference_document_version.editable():
            if quota:
                if self.user.has_perm("reference_documents.change_preferentialquotaordernumber"):
                    actions += f"<a href='{reverse('reference_documents:preferential_quotas_edit', args=[quota.pk])}'>Edit</a>"
                if self.user.has_perm("reference_documents.delete_preferentialquotaordernumber"):
                    actions += f" | <a href='{reverse('reference_documents:preferential_quotas_delete', args=[quota.pk, quota.ref_order_number.reference_document_version.pk])}'>Delete</a>"

        row_to_add = [
            {
                "html": comm_code_link,
            },
            {
                "text": duty_rate,
            },
            {
                "text": f"{volume} {measurement}",
            },
            {
                "text": valid_between,
            },
            {
                "html": actions,
            },
        ]

        return row_to_add

    def get_suspension_row(self, quota_valid_between, suspension, commodity_code, reference_document_version, templated=False):

        # comm_code = ReferenceDocumentVersionContext.get_tap_comm_code(
        #     self.reference_document_version,
        #     commodity_code,
        # )
        # if comm_code:
        #     comm_code_link = f'<a class="govuk-link" href="{comm_code.get_url()}">{comm_code.structure_code}</a>'
        # else:
        comm_code_link = f"{commodity_code}"

        actions = "<span></span>"

        if self.reference_document_version.editable():
            if not templated:
                if self.user.has_perm("reference_documents.change_preferentialquotasuspension"):
                    actions += f"<a href='{reverse('reference_documents:preferential-quotas-suspension-edit', args=[suspension.pk])}'>Edit</a>"
                if self.user.has_perm("reference_documents.delete_preferentialquotasuspension"):
                    actions += f" | <a href='{reverse('reference_documents:preferential-quota-suspension-delete', args=[suspension.pk, reference_document_version.pk])}'>Delete</a>"

        row_to_add = [
            {
                "html": comm_code_link,
            },
            {
                "text": suspension.valid_between,
            },
            {
                "text": quota_valid_between,
            },
            {
                "html": actions,
            },
        ]

        return row_to_add

    def order_number_rows(self, data, ref_doc_order_number):
        # Add Data Rows
        for quota in ref_doc_order_number.preferential_quotas.order_by(
                "commodity_code",
        ):
            row_to_add = self.get_quota_row(quota.commodity_code, quota.volume, quota.measurement, quota.duty_rate, quota.valid_between, quota)

            data[ref_doc_order_number.quota_order_number]["data_rows"].append(
                row_to_add,
            )

    def order_number_suspension_rows(self, data, ref_doc_order_number):
        for suspension in RefQuotaSuspension.objects.all().filter(
                preferential_quota__ref_order_number__quota_order_number=ref_doc_order_number
        ).order_by(
            "preferential_quota__commodity_code",
        ):
            row_to_add = self.get_suspension_row(
                suspension.preferential_quota.vaid_between,
                suspension.preferential_quota,
                suspension.preferential_quota.commodity_code,
                suspension.preferential_quota.ref_order_number.reference_document_version,
                False
            )

            data[ref_doc_order_number.quota_order_number]["suspension_data_rows"].append(
                row_to_add,
            )

    def templated_order_number_suspension_rows(self, data, ref_doc_order_number):
        for templated_suspension in RefQuotaSuspensionRange.objects.all().filter(
                ref_quota_definition_range__ref_order_number=ref_doc_order_number
        ):

            data_to_add = {
                'data_rows': [],
                'preferential_quota_suspension_template': templated_suspension
            }

            if templated_suspension.pk not in data[ref_doc_order_number.quota_order_number]["templated_suspension_data"].keys():
                data[ref_doc_order_number.quota_order_number]["templated_suspension_data"][templated_suspension.pk] = []

            for suspension in templated_suspension.dynamic_preferential_quota_suspensions():
                row_to_add = self.get_suspension_row(
                    suspension.preferential_quota.valid_between,
                    suspension,
                    suspension.preferential_quota.commodity_code,
                    suspension.preferential_quota.ref_order_number.reference_document_version,
                    templated=True
                )

                data_to_add['data_rows'].append(
                    row_to_add
                )

            data[ref_doc_order_number.quota_order_number]["templated_data"][templated_suspension.ref_quota_definition_range.commodity_code].append(data_to_add)

    def templated_order_number_rows(self, data, ref_doc_order_number):
        # Add templated data rows

        for quota_template in ref_doc_order_number.ref_quota_definition_range.order_by("commodity_code"):

            data_to_add = {
                'data_rows': [],
                'ref_quota_definition_range': quota_template
            }

            if quota_template.commodity_code not in data[ref_doc_order_number.quota_order_number]["templated_data"].keys():
                data[ref_doc_order_number.quota_order_number]["templated_data"][quota_template.commodity_code] = []

            for quota in quota_template.dynamic_preferential_quotas():
                row_to_add = self.get_quota_row(quota.commodity_code, quota.volume, quota.measurement, quota.duty_rate, quota.valid_between)

                data_to_add['data_rows'].append(
                    row_to_add
                )

            data[ref_doc_order_number.quota_order_number]["templated_data"][quota_template.commodity_code].append(data_to_add)


class ReferenceDocumentVersionDetails(PermissionRequiredMixin, DetailView):
    template_name = "reference_documents/reference_document_versions/details.jinja"
    permission_required = "reference_documents.view_referencedocumentversion"
    model = ReferenceDocumentVersion

    def get_context_data(self, *args, **kwargs):
        context = super(ReferenceDocumentVersionDetails, self).get_context_data(
            *args,
            **kwargs,
        )

        # title
        context["ref_doc_title"] = (
            f"Reference document for {context['object'].reference_document.get_area_name_by_area_id()}"
        )

        context_data = ReferenceDocumentVersionContext(context["object"], self.request.user)

        # rates
        context["rate_data"] = context_data.duties_row_data()
        context["rate_headers"] = context_data.duties_headers()

        # Order numbers
        context['order_numbers'] = context_data.order_numbers

        # headers
        context["quota_definition_headers"] = (
            context_data.quotas_headers()
        )
        context["suspension_headers"] = (
            context_data.suspension_headers()
        )
        return context


class ReferenceDocumentVersionCreate(PermissionRequiredMixin, CreateView):
    template_name = "reference_documents/reference_document_versions/create.jinja"
    permission_required = "reference_documents.add_referencedocumentversion"
    form_class = ReferenceDocumentVersionsCreateUpdateForm

    def get_initial(self):
        initial = super().get_initial()
        initial["reference_document"] = ReferenceDocument.objects.all().get(
            pk=self.kwargs["pk"],
        )
        return initial

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
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
    form_class = ReferenceDocumentVersionsCreateUpdateForm

    def get_success_url(self):
        return reverse(
            "reference_documents:version-confirm-update",
            kwargs={"pk": self.object.pk},
        )


class ReferenceDocumentVersionDelete(PermissionRequiredMixin, DeleteView):
    form_class = ReferenceDocumentVersionDeleteForm
    model = ReferenceDocumentVersion
    permission_required = "reference_documents.delete_referencedocumentversion"
    template_name = "reference_documents/reference_document_versions/delete.jinja"

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
            self.request.session["deleted_version"] = {
                "ref_doc_pk": f"{self.object.reference_document.pk}",
                "area_id": f"{self.object.reference_document.area_id}",
                "version": f"{self.object.version}",
            }
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
    model = ReferenceDocumentVersion


class ReferenceDocumentVersionConfirmUpdate(DetailView):
    template_name = (
        "reference_documents/reference_document_versions/confirm_update.jinja"
    )
    model = ReferenceDocumentVersion


class ReferenceDocumentVersionConfirmDelete(TemplateView):
    template_name = (
        "reference_documents/reference_document_versions/confirm_delete.jinja"
    )

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["deleted_pk"] = self.kwargs["deleted_pk"]
        return context_data


class ReferenceDocumentVersionChangeStateToInReview(
    PermissionRequiredMixin,
    DetailView,
):
    template_name = "reference_documents/reference_document_versions/confirm_state_to_in_review.jinja"
    model = ReferenceDocumentVersion
    permission_required = "reference_documents.change_referencedocumentversion"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Update state
        # self.object.in_review()

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["ref_doc_pk"] = self.kwargs["ref_doc_pk"]
        return context_data

    def get(self, request, *args, **kwargs):
        rdv = ReferenceDocumentVersion.objects.all().get(pk=self.kwargs["pk"])
        rdv.in_review()
        rdv.save(force_save=True)
        return super().get(request, *args, **kwargs)


class ReferenceDocumentVersionChangeStateToPublished(
    PermissionRequiredMixin,
    DetailView,
):
    template_name = "reference_documents/reference_document_versions/confirm_state_to_published.jinja"
    model = ReferenceDocumentVersion
    permission_required = "reference_documents.change_referencedocumentversion"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Update state
        # self.object.in_review()

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["ref_doc_pk"] = self.kwargs["ref_doc_pk"]
        return context_data

    def get(self, request, *args, **kwargs):
        rdv = ReferenceDocumentVersion.objects.all().get(pk=self.kwargs["pk"])
        rdv.published()
        rdv.save(force_save=True)
        return super().get(request, *args, **kwargs)


class ReferenceDocumentVersionChangeStateToEditable(
    PermissionRequiredMixin,
    DetailView,
):
    template_name = "reference_documents/reference_document_versions/confirm_state_to_editable.jinja"
    model = ReferenceDocumentVersion
    permission_required = "reference_documents.change_referencedocumentversion"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Update state
        # self.object.in_review()

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["ref_doc_pk"] = self.kwargs["ref_doc_pk"]
        return context_data

    def get(self, request, *args, **kwargs):
        rdv = ReferenceDocumentVersion.objects.all().get(pk=self.kwargs["pk"])
        if rdv.status == ReferenceDocumentVersionStatus.PUBLISHED:
            if request.user.is_superuser:
                rdv.editing_from_published()
                rdv.save(force_save=True)
            else:
                raise PermissionDenied()
        elif rdv.status == ReferenceDocumentVersionStatus.IN_REVIEW:
            rdv.editing_from_in_review()
            rdv.save(force_save=True)

        return super().get(request, *args, **kwargs)


class ReferenceDocumentVersionAlignmentCheck(DetailView):
    template_name = "reference_documents/reference_document_versions/checks.jinja"
    model = ReferenceDocumentVersion
    permission_required = "reference_documents.view_alignmentreportcheck"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        last_alignment_report = self.object.alignment_reports.all().filter(
            status=AlignmentReportStatus.COMPLETE
        ).last()

        if last_alignment_report:
            context["last_alignment_report"] = last_alignment_report
            context['alignment_report_stats'] = self.alignment_report_stats_context(last_alignment_report)
            context["last_run"] = last_alignment_report.created_at.strftime('%Y-%m-%d %H:%M')
        else:
            context["last_alignment_report"] = None
            context['alignment_report_stats'] = None
            context["last_run"] = None
        return context

    def alignment_report_stats_context(self, alignment_report: AlignmentReport):
        stats = []

        for key, value in alignment_report.check_stats().items():
            percentage_calc = '-'

            if value['total'] > 0 and value['failed'] > 0:
                percentage_calc = round((value['failed'] / value['total']) * 100, 1)

            row = [
                {"text": key},
                {"text": value['total']},
                {"text": value['passed']},
                {"text": value['warning']},
                {"text": value['failed']},
                {"text": value['skipped']},
                {"text": percentage_calc},
            ]
            stats.append(row)

        return stats

    def post(self, request, *args, **kwargs):
        if request.user.has_perm("reference_documents.add_alignmentreportcheck"):
            # Queue alignment check to background worker
            run_alignment_check.delay(self.kwargs['pk'])

            return redirect('reference_documents:alignment-check-queued', pk=self.kwargs['pk'])
        else:
            return HttpResponseForbidden()


class ReferenceDocumentVersionAlignmentCheckQueued(DetailView):
    template_name = "reference_documents/reference_document_versions/check_queued.jinja"
    model = ReferenceDocumentVersion


class ReferenceDocumentVersionCheckResults(ListView):
    model = AlignmentReportCheck
    template_name = (
        "reference_documents/reference_document_versions/check_results.jinja"
    )
    context_object_name = "checks"

    @property
    def reference_document_version(self) -> ReferenceDocumentVersion:
        return ReferenceDocumentVersion.objects.all().get(pk=self.kwargs["pk"])

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["reference_document_version"] = self.reference_document_version
        return context

    def get_queryset(self):
        alignment_checks = AlignmentReportCheck.objects.all().filter(
            alignment_report__reference_document_version=self.reference_document_version,
        )
        queryset = {
            "ref_rates": alignment_checks.filter(
                ref_rate__isnull=False,
            ),
            "ref_quota_definitions": alignment_checks.filter(
                ref_quota_definition__isnull=False,
            ),
            "ref_order_numbers": alignment_checks.filter(
                ref_order_number__isnull=False,
            ),
        }
        return queryset
