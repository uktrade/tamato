from datetime import date
from os import path
from tempfile import NamedTemporaryFile
from urllib.parse import urlencode

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.urls import reverse_lazy
from django.views.generic import DetailView
from django.views.generic import FormView
from django.views.generic import TemplateView

from common.util import format_date_string
from common.views import RequiresSuperuserMixin
from common.views import WithPaginationListView
from importer import forms
from importer import models
from importer.filters import ImportBatchFilter
from importer.filters import TaricImportFilter
from importer.goods_report import GoodsReporter
from importer.models import ImportBatch
from importer.models import ImportBatchStatus
from notifications.models import GoodsSuccessfulImportNotification
from notifications.models import Notification
from notifications.models import NotificationTypeChoices
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus


class ImportBatchList(RequiresSuperuserMixin, WithPaginationListView):
    """UI endpoint for viewing and filtering General Import Batches."""

    queryset = (
        models.ImportBatch.objects.all()
        .order_by("-created_at")
        .annotate(
            chunks_done=Count(
                "chunks",
                filter=Q(chunks__status=models.ImporterChunkStatus.DONE),
            ),
            chunks_running=Count(
                "chunks",
                filter=Q(chunks__status=models.ImporterChunkStatus.RUNNING),
            ),
            chunks_waiting=Count(
                "chunks",
                filter=Q(chunks__status=models.ImporterChunkStatus.WAITING),
            ),
            chunks_errored=Count(
                "chunks",
                filter=Q(chunks__status=models.ImporterChunkStatus.ERRORED),
            ),
        )
    )
    template_name = "importer/list.jinja"
    filterset_class = ImportBatchFilter


class UploadTaricFileView(RequiresSuperuserMixin, FormView):
    form_class = forms.UploadTaricForm
    fields = ["name", "split_job"]
    success_url = reverse_lazy("import_batch-ui-list")
    template_name = "importer/create.jinja"

    def form_valid(self, form):
        form.save(user=self.request.user)
        return super().form_valid(form)


class CommodityImportListView(
    PermissionRequiredMixin,
    WithPaginationListView,
):
    """UI endpoint for viewing and filtering TARIC file imports."""

    permission_required = [
        "common.add_trackedmodel",
        "common.change_trackedmodel",
    ]
    queryset = models.ImportBatch.objects.filter(
        goods_import=True,
    ).order_by("-created_at")
    template_name = "eu-importer/select-imports.jinja"
    filterset_class = TaricImportFilter

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        import_status = self.request.GET.get("status")
        workbasket_status = self.request.GET.get("workbasket__status")

        context["selected_link"] = "all"

        if (
            import_status == ImportBatchStatus.SUCCEEDED
            and workbasket_status == WorkflowStatus.EDITING
        ):
            context["selected_link"] = "ready"
        elif (
            import_status == ImportBatchStatus.SUCCEEDED
            and workbasket_status == WorkflowStatus.PUBLISHED
        ):
            context["selected_link"] = "published"
        elif (
            import_status == ImportBatchStatus.SUCCEEDED
            and workbasket_status == WorkflowStatus.ARCHIVED
        ):
            context["selected_link"] = "empty"
        elif import_status == ImportBatchStatus.IMPORTING:
            context["selected_link"] = "importing"
        elif import_status == ImportBatchStatus.FAILED:
            context["selected_link"] = "failed"

        context["goods_status"] = self.goods_status
        context["status_tag_generator"] = self.status_tag_generator

        return context

    @classmethod
    def goods_status(cls, import_batch: ImportBatchFilter) -> str:
        """Returns the goods status of an ImportBatch instance, used to
        determine rendered output of the goods status column in this list view's
        template."""
        workbasket = import_batch.workbasket

        if (
            import_batch.status == ImportBatchStatus.SUCCEEDED
            and workbasket
            and workbasket.status == WorkflowStatus.EDITING
        ):
            return "editable_goods"
        elif (
            import_batch.status == ImportBatchStatus.SUCCEEDED
            and import_batch.taric_file
            and (not workbasket or workbasket.status == WorkflowStatus.ARCHIVED)
        ):
            # ImportBatch instances without a `taric_file` object are legacy
            # instances and are not considered to have "no_goods" status.
            return "no_goods"
        else:
            # All other statuses are considered empty.
            return "empty"

    @classmethod
    def status_tag_generator(cls, import_batch: ImportBatchFilter) -> dict:
        """Returns a dict with text and a css class for a ui friendly label for
        an import batch."""
        workbasket = import_batch.workbasket

        if import_batch.status:
            if import_batch.status == ImportBatchStatus.IMPORTING:
                return {"text": "IMPORTING", "tag_class": "status-badge"}

            elif import_batch.status == ImportBatchStatus.FAILED:
                return {"text": "FAILED", "tag_class": "status-badge-red"}
            elif import_batch.status == ImportBatchStatus.FAILED_EMPTY:
                return {"text": "EMPTY", "tag_class": "status-badge-grey"}

            if workbasket:
                if (
                    import_batch.status == ImportBatchStatus.SUCCEEDED
                    and workbasket.status == WorkflowStatus.EDITING
                ):
                    return {"text": "READY", "tag_class": "status-badge-purple"}

                elif (
                    import_batch.status == ImportBatchStatus.SUCCEEDED
                    and workbasket.status == WorkflowStatus.PUBLISHED
                ):
                    return {"text": "PUBLISHED", "tag_class": "status-badge-green"}

                elif (
                    import_batch.status == ImportBatchStatus.SUCCEEDED
                    and workbasket.status == WorkflowStatus.ARCHIVED
                ):
                    return {"text": "EMPTY", "tag_class": "status-badge-grey"}

            else:
                return {"text": ""}


class CommodityImportCreateView(
    PermissionRequiredMixin,
    FormView,
):
    """Commodity code file import view."""

    form_class = forms.CommodityImportForm
    permission_required = [
        "common.add_trackedmodel",
        "common.change_trackedmodel",
    ]
    template_name = "eu-importer/import.jinja"

    def get_success_url(self):
        return reverse_lazy(
            "commodity_importer-ui-success",
            kwargs={"pk": self.object.pk},
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        self.object = form.save()

        return redirect(
            reverse(
                "commodity_importer-ui-create-success",
                kwargs={"pk": self.object.pk},
            ),
        )


class CommodityImportDetails(RequiresSuperuserMixin, DetailView):
    """UI endpoint for viewing details of a TARIC parser import, and view
    failures and errors."""

    model = ImportBatch
    queryset = ImportBatch.objects.all()
    template_name = "eu-importer/details.jinja"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["issues"] = context["object"].issues.all()
        return context


class CommodityImportCreateSuccessView(DetailView):
    """Commodity code import success view."""

    template_name = "eu-importer/import-success.jinja"
    model = models.ImportBatch


class DownloadAdminTaricView(RequiresSuperuserMixin, DetailView):
    model = models.ImportBatch

    def download_response(self, import_batch: models.ImportBatch) -> HttpResponse:
        """Returns a response object with associated payload containing the
        contents of `import_batch.taric_file`."""

        file_content = import_batch.taric_file.read()
        response = HttpResponse(file_content)
        response["content-type"] = "text/xml"
        response["content-length"] = len(file_content)
        response["content-disposition"] = (
            f'attachment; filename="{import_batch.taric_file.name}"'
        )
        return response

    def get(self, request, *args, **kwargs) -> HttpResponse:
        import_batch = self.get_object()
        return self.download_response(import_batch)


class DownloadGoodsReportMixin:
    def download_response(self, import_batch: models.ImportBatch) -> HttpResponse:
        """Returns a response object with associated payload containing the
        contents of a generated goods report in Excel format."""

        taric_file = path.splitext(import_batch.name)[0]
        report_name = f"comm_code_changes_in_{taric_file}.xlsx"

        with NamedTemporaryFile(suffix=".xlsx") as tmp:
            reporter = GoodsReporter(import_batch.taric_file)
            goods_report = reporter.create_report()
            goods_report.xlsx_file(tmp)
            file_content = tmp.read()

        response = HttpResponse(file_content)
        response["content-type"] = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["content-length"] = len(file_content)
        response["content-disposition"] = f'attachment; filename="{report_name}"'
        return response


class DownloadGoodsReportView(
    DownloadGoodsReportMixin,
    PermissionRequiredMixin,
    DetailView,
):
    """View used to download an import report of goods changes in Excel
    format."""

    permission_required = "common.add_trackedmodel"
    model = models.ImportBatch

    def get(self, request, *args, **kwargs) -> HttpResponse:
        import_batch = self.get_object()
        return self.download_response(import_batch)


class NotifyGoodsReportView(
    PermissionRequiredMixin,
    DetailView,
):
    """View used to notify an import report of goods changes in Excel format."""

    permission_required = "common.add_trackedmodel"
    model = models.ImportBatch

    def get(self, request, *args, **kwargs):
        import_batch = self.get_object()

        # create notification
        notification = GoodsSuccessfulImportNotification(
            notified_object_pk=import_batch.id,
        )
        notification.save()
        notification.synchronous_send_emails()

        return redirect(
            reverse("goods-report-notify-success", kwargs={"pk": import_batch.id}),
        )


class NotifyGoodsReportSuccessView(DetailView):
    """Goods Report notification success trigger view."""

    template_name = "eu-importer/notify-success.jinja"
    model = models.ImportBatch


class ImportedGoodsReview(
    PermissionRequiredMixin,
    TemplateView,
):
    """UI endpoint for reviewing goods changes from an imported Taric file."""

    template_name = "eu-importer/review-imported-goods.jinja"
    permission_required = "workbaskets.view_workbasket"

    @property
    def workbasket(self):
        return WorkBasket.objects.get(pk=self.kwargs["pk"])

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["tab_page_title"] = "Review commodities"
        context["selected_tab"] = "commodities"
        context["user_workbasket"] = WorkBasket.current(self.request)
        context["workbasket"] = self.workbasket
        context["report_lines"] = []
        context["import_batch_pk"] = None

        # Get actual values from the ImportBatch instance if one is associated
        # with the workbasket.
        try:
            import_batch = self.workbasket.importbatch
        except ObjectDoesNotExist:
            import_batch = None

        taric_file = None
        if import_batch and import_batch.taric_file and import_batch.taric_file.name:
            taric_file = import_batch.taric_file.storage.exists(
                import_batch.taric_file.name,
            )

        if taric_file:
            reporter = GoodsReporter(import_batch.taric_file)
            goods_report = reporter.create_report()
            today = date.today()

            context["report_lines"] = [
                {
                    "update_type": line.update_type.title() if line.update_type else "",
                    "record_name": line.record_name.title() if line.record_name else "",
                    "item_id": line.goods_nomenclature_item_id,
                    "item_id_search_url": (
                        reverse("commodity-ui-list")
                        + "?"
                        + urlencode({"item_id": line.goods_nomenclature_item_id})
                        if line.goods_nomenclature_item_id
                        else ""
                    ),
                    "measures_search_url": (
                        reverse("measure-ui-list")
                        + "?"
                        + urlencode(
                            {
                                "goods_nomenclature__item_id": line.goods_nomenclature_item_id,
                                "end_date_modifier": "after",
                                "end_date_0": today.day,
                                "end_date_1": today.month,
                                "end_date_2": today.year,
                            },
                        )
                        if line.goods_nomenclature_item_id
                        else ""
                    ),
                    "suffix": line.suffix,
                    "start_date": format_date_string(
                        line.validity_start_date,
                        short_format=True,
                    ),
                    "end_date": format_date_string(
                        line.validity_end_date,
                        short_format=True,
                    ),
                    "comments": line.comments,
                }
                for line in goods_report.report_lines
            ]
            context["import_batch_pk"] = import_batch.pk

            # notifications only relevant to a goods import
            if context["workbasket"] == context["user_workbasket"]:
                context["unsent_notification"] = (
                    import_batch.goods_import
                    and not Notification.objects.filter(
                        notified_object_pk=import_batch.pk,
                        notification_type=NotificationTypeChoices.GOODS_REPORT,
                    ).exists()
                )

        return context
