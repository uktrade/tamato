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
]

urlpatterns = general_importer_urlpatterns + commodity_importer_urlpatterns
