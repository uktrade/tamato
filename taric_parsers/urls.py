from django.urls import path

from importer import views

importer_urlpatterns = [
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

urlpatterns = importer_urlpatterns
