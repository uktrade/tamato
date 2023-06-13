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
        # TODO
        # Rename
        views.CommodityImportView.as_view(),
        # views.TaricImportCreateView.as_view(),
        name="commodity_importer-ui-create",
        # was commodity-ui-import
    ),
    path(
        "commodity-importer/success/",
        # TODO
        # Rename
        views.CommodityImportSuccessView.as_view(),
        # views.TaricImportSuccessView.as_view(),
        name="commodity_importer-ui-success",
        # was commodity-ui-import-success
    ),
]

urlpatterns = general_importer_urlpatterns + commodity_importer_urlpatterns
