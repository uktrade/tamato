import uuid

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Count
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse
from django.urls import reverse_lazy
from django.views.generic import DetailView
from django.views.generic import FormView
from django.views.generic.base import RedirectView

from commodities.models import GoodsNomenclature
from commodities.models import GoodsNomenclatureDescription
from commodities.models import GoodsNomenclatureIndent
from commodities.models import GoodsNomenclatureOrigin
from commodities.models import GoodsNomenclatureSuccessor
from common.views import RequiresSuperuserMixin
from common.views import WithPaginationListView
from importer import forms
from importer import models
from importer.filters import ImportBatchFilter
from importer.filters import TaricImportFilter
from workbaskets.models import WorkBasket


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
    queryset = models.ImportBatch.objects.order_by("-created_at")
    template_name = "eu-importer/select-imports.jinja"
    filterset_class = TaricImportFilter


class CommodityImportDetailURLResolverView(RedirectView):
    """URL resolver view used to redirect to the appropriate 'detail' view for
    an ImportBatch instance at run-time."""

    def get_redirect_url(self, *args, **kwargs):
        # Fetch the import_batch to get the related workbasket.
        import_batch = models.ImportBatch.objects.get(pk=kwargs["pk"])

        status_to_location_map = {
            models.ImportBatchStatus.UPLOADING: {
                "path_name": "commodity_importer-ui-create-success",
                "kwargs": {
                    "pk": str(import_batch.pk),
                },
            },
            # TODO: is the IMPORTED status required or should a successful import transition directly to REVIEW?
            models.ImportBatchStatus.IMPORTED: {
                "path_name": "commodity_importer-ui-create-success",
                "kwargs": {
                    "pk": str(import_batch.pk),
                },
            },
            models.ImportBatchStatus.REVIEW: {
                "path_name": "commodity_importer-ui-changes",
                "kwargs": str(import_batch.pk),
            },
            # TODO: which workbasket view? workbasket:workbasket-ui-changes (pk=import.workbasket.pk)?
            models.ImportBatchStatus.COMPLETED: {
                "path_name": "commodity_importer-ui-list",
                "kwargs": {},
            },
            # TODO: will there be a view for failed imports?
            models.ImportBatchStatus.FAILED: {
                "path_name": "commodity_importer-ui-list",
                "kwargs": {},
            },
        }

        location = status_to_location_map[import_batch.status]
        return reverse(location["path_name"], kwargs=location["kwargs"])


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
    success_url = reverse_lazy("commodity_importer-ui-success")
    template_name = "eu-importer/import.jinja"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        unique_id = str(uuid.uuid4())
        workbasket = WorkBasket.objects.create(
            title=f"Commodity codes import - {unique_id}",
            author=self.request.user,
        )
        self.object = form.save(workbasket)
        workbasket.reason = (
            f"Imported from file {self.object.name} - "
            f"pending review and completion."
        )
        workbasket.save()

        return redirect(
            reverse(
                "commodity_importer-ui-create-success",
                kwargs={"pk": self.object.pk},
            ),
        )


class CommodityImportCreateSuccessView(DetailView):
    """Commodity code import success view."""

    template_name = "eu-importer/import-success.jinja"
    model = models.ImportBatch


class CommodityImportChangesView(DetailView):
    """Commodity code import changes view."""

    template_name = "eu-importer/import-changes.jinja"
    model = models.ImportBatch

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        workbasket = WorkBasket.objects.filter(reason__contains=self.object.name).last()
        tracked_models = workbasket.tracked_models
        import_changes = []

        # Each tracked model represents an import change
        for obj in tracked_models:
            obj_data = {
                "update_type": obj.update_type_str,
                "object": obj._meta.verbose_name.title(),
            }
            if isinstance(obj, GoodsNomenclature):
                obj_data.update(
                    {
                        "goods_nomenclature": obj.item_id,
                        "suffix": obj.suffix,
                        "validity_start": obj.valid_between.lower,
                        "validity_end": obj.valid_between.upper
                        if obj.valid_between.upper
                        else "-",
                        "comments": f"Description: {obj.structure_description}",
                    },
                )
            elif isinstance(obj, GoodsNomenclatureIndent):
                obj_data.update(
                    {
                        "goods_nomenclature": obj.indented_goods_nomenclature,
                        "suffix": obj.indented_goods_nomenclature.suffix,
                        "validity_start": obj.validity_start,
                        "validity_end": "-",
                        "comments": f"Indent: {obj.indent}",
                    },
                )
            elif isinstance(obj, GoodsNomenclatureDescription):
                obj_data.update(
                    {
                        "goods_nomenclature": obj.described_goods_nomenclature,
                        "suffix": obj.described_goods_nomenclature.suffix,
                        "validity_start": obj.validity_start,
                        "validity_end": "-",
                        "comments": f"Description: {obj.description}",
                    },
                )
            elif isinstance(obj, GoodsNomenclatureOrigin):
                obj_data.update(
                    {
                        "goods_nomenclature": obj.new_goods_nomenclature,
                        "suffix": obj.new_goods_nomenclature.suffix,
                        "validity_start": "-",
                        "validity_end": "-",
                        "comments": obj.__str__(),
                    },
                )
            elif isinstance(obj, GoodsNomenclatureSuccessor):
                obj_data.update(
                    {
                        "goods_nomenclature": obj.absorbed_into_goods_nomenclature,
                        "suffix": obj.absorbed_into_goods_nomenclature.suffix,
                        "validity_start": "-",
                        "validity_end": "-",
                        "comments": obj.__str__(),
                    },
                )

            import_changes.append(obj_data)

        context["import_changes"] = import_changes
        return context
