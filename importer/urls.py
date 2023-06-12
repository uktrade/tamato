from django.urls import path

from importer import views

urlpatterns = [
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
    # new comm code importer url
    path(
        "eu-importer/",
        views.TaricImportList.as_view(),
        name="eu_import_batch-ui-list",
    ),
]
