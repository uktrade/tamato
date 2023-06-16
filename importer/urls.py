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

commodity_importer_urlpatterns = [
    path(
        "commodity-importer/<pk>/detail/",
        views.CommodityImportDetailURLResolverView.as_view(),
        name="commodity_importer-ui-detail-url-resolver",
    ),
    path(
        "commodity-importer/",
        views.CommodityImportListView.as_view(),
        name="commodity_importer-ui-list",
    ),
    path(
        "commodity-importer/create/",
        # TODO
        # Rename
        views.CommodityImportCreateView.as_view(),
        # views.TaricImportCreateView.as_view(),
        name="commodity_importer-ui-create",
        # was commodity-ui-import
    ),
    path(
        "commodity-importer/create/<pk>/success/",
        # TODO
        # Rename
        views.CommodityImportCreateSuccessView.as_view(),
        # views.TaricImportSuccessView.as_view(),
        name="commodity_importer-ui-create-success",
        # was commodity-ui-import-success
    ),
    path(
        "commodity-importer/<pk>/changes",
        views.CommodityImportChangesView.as_view(),
        name="commodity_importer-ui-changes",
    ),
]

urlpatterns = general_importer_urlpatterns + commodity_importer_urlpatterns
