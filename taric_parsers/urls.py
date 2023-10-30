from django.urls import path

from taric_parsers import views

importer_urlpatterns = [
    path(
        "taric_parser/<pk>/details/",
        views.TaricImportDetails.as_view(),
        name="taric_parser_import_ui_details",
    ),
    path(
        "taric_parser/",
        views.TaricImportList.as_view(),
        name="taric_parser_import_ui_list",
    ),
    path(
        "taric_parser/create/",
        views.TaricImportUpload.as_view(),
        name="taric_parser_import_ui_create",
    ),
]

urlpatterns = importer_urlpatterns
