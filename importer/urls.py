from django.urls import path

from importer import views

general_importer_urlpatterns = [
    path(
        "importer/",
        views.ImportBatchList.as_view(),
        name="import_batch-ui-list",
    ),
    path(
        "importer/create/",
        views.UploadTaricFileView.as_view(),
        name="import_batch-ui-create",
    ),
]

new_general_importer_urlpatterns = [
    path(
        "new_importer/<pk>/details/",
        views.NewImportBatchDetails.as_view(),
        name="new_import_batch_details",
    ),
    path(
        "new_importer/",
        views.NewImportBatchList.as_view(),
        name="new_import_batch-ui-list",
    ),
    path(
        "new_importer/create/",
        views.NewUploadTaricFileView.as_view(),
        name="new_import_batch-ui-create",
    ),
]

commodity_importer_urlpatterns = [
    path(
        "commodity-importer/",
        views.CommodityImportListView.as_view(),
        name="commodity_importer-ui-list",
    ),
    path(
        "commodity-importer/create/",
        views.CommodityImportCreateView.as_view(),
        name="commodity_importer-ui-create",
    ),
    path(
        "commodity-importer/create/<pk>/success/",
        views.CommodityImportCreateSuccessView.as_view(),
        name="commodity_importer-ui-create-success",
    ),
    path(
        "download-admin-envelope/<pk>/",
        views.DownloadAdminTaricView.as_view(),
        name="admin-taric-ui-download",
    ),
    path(
        "download-goods-report/<pk>/",
        views.DownloadGoodsReportView.as_view(),
        name="goods-report-ui-download",
    ),
]

urlpatterns = (
    general_importer_urlpatterns
    + commodity_importer_urlpatterns
    + new_general_importer_urlpatterns
)
