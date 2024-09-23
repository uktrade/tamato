from django.urls import include
from django.urls import path

from tasks import views

app_name = "workflow"

ui_patterns = [
    path("create/", views.TaskCreateView.as_view(), name="task-ui-create"),
    path(
        "<int:pk>/confirm-create",
        views.TaskConfirmCreateView.as_view(),
        name="task-ui-confirm-create",
    ),
]

urlpatterns = [
    path("tasks/", include(ui_patterns)),
]
