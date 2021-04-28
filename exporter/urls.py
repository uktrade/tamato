from django.urls import path

from exporter import views

urlpatterns = [
    path(
        "api/activity-stream/",
        views.activity_stream,
        name="activity-stream",
    ),
    path(
        "api/schema.dbml",
        views.dbml_schema,
        name="dbml-schema",
    ),
]
